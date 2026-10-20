// Run the production tiling shader and batching helper on Vulkan. Forced small
// batches expose texel-offset mistakes without allocating a huge test texture.
#include <vulkan/vulkan.h>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>
#include "video_core/host_shaders/tiling_micro_32_comp.h"
#include "video_core/texture_cache/tiling_dispatch.h"

static void Check(VkResult result) {
    if (result != VK_SUCCESS) throw std::runtime_error("Vulkan test operation failed: " + std::to_string(result));
}
struct Buffer { VkBuffer handle; VkDeviceMemory memory; void* mapped; };

int main() try {
    // Boundaries observed in Ratchet plus exact-limit and invalid-input cases.
    for (uint32_t groups : {0u, 1u, 65535u, 65536u, 65537u, 524288u, 700416u}) {
        uint64_t covered = 0;
        assert(VideoCore::ForEachTilingDispatch(groups, 65536, [&](uint32_t base, uint32_t count) {
            assert(base == covered * 64 && count > 0 && count <= 65536);
            covered += count;
        }));
        assert(covered == groups);
    }
    assert(!VideoCore::ForEachTilingDispatch(1, 0, [](auto, auto) { assert(false); }));
    assert(!VideoCore::ForEachTilingDispatch(UINT32_MAX, 65536, [](auto, auto) { assert(false); }));

    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
    app.apiVersion = VK_API_VERSION_1_3;
    VkInstanceCreateInfo instance_info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    instance_info.pApplicationInfo = &app;
    VkInstance instance;
    Check(vkCreateInstance(&instance_info, nullptr, &instance));
    uint32_t physical_count = 1;
    VkPhysicalDevice physical;
    Check(vkEnumeratePhysicalDevices(instance, &physical_count, &physical));
    uint32_t family_count = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &family_count, nullptr);
    std::vector<VkQueueFamilyProperties> families(family_count);
    vkGetPhysicalDeviceQueueFamilyProperties(physical, &family_count, families.data());
    uint32_t family = 0;
    while (family < family_count && !(families[family].queueFlags & VK_QUEUE_COMPUTE_BIT)) ++family;
    if (family == family_count) throw std::runtime_error("No compute queue");
    float priority = 1;
    VkDeviceQueueCreateInfo queue_info{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
    queue_info.queueFamilyIndex = family; queue_info.queueCount = 1; queue_info.pQueuePriorities = &priority;
    VkPhysicalDeviceScalarBlockLayoutFeatures scalar{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SCALAR_BLOCK_LAYOUT_FEATURES};
    scalar.scalarBlockLayout = VK_TRUE;
    VkDeviceCreateInfo device_info{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
    device_info.pNext = &scalar; device_info.queueCreateInfoCount = 1; device_info.pQueueCreateInfos = &queue_info;
    VkDevice device;
    Check(vkCreateDevice(physical, &device_info, nullptr, &device));
    VkQueue queue;
    vkGetDeviceQueue(device, family, 0, &queue);
    VkPhysicalDeviceMemoryProperties memory_properties;
    vkGetPhysicalDeviceMemoryProperties(physical, &memory_properties);
    const auto make_buffer = [&](VkDeviceSize size, VkBufferUsageFlags usage) {
        Buffer result{};
        VkBufferCreateInfo info{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        info.size = size; info.usage = usage;
        Check(vkCreateBuffer(device, &info, nullptr, &result.handle));
        VkMemoryRequirements requirements;
        vkGetBufferMemoryRequirements(device, result.handle, &requirements);
        uint32_t type = 0;
        constexpr auto flags = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
        while (type < memory_properties.memoryTypeCount &&
               (!(requirements.memoryTypeBits & (1u << type)) ||
                (memory_properties.memoryTypes[type].propertyFlags & flags) != flags)) ++type;
        if (type == memory_properties.memoryTypeCount) throw std::runtime_error("No coherent host memory");
        VkMemoryAllocateInfo allocation{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        allocation.allocationSize = requirements.size; allocation.memoryTypeIndex = type;
        Check(vkAllocateMemory(device, &allocation, nullptr, &result.memory));
        Check(vkBindBufferMemory(device, result.handle, result.memory, 0));
        Check(vkMapMemory(device, result.memory, 0, size, 0, &result.mapped));
        return result;
    };
    constexpr uint32_t texels = 128 * 128;
    constexpr VkDeviceSize bytes = texels * 4;
    auto tiled = make_buffer(bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto input = make_buffer(bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto output = make_buffer(bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    auto params = make_buffer(12 + 16 * 16, VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);
    std::memset(params.mapped, 0, 12 + 16 * 16);
    const std::array<uint32_t, 7> info{0, 1, 1, bytes, 128, 128, 0};
    std::memcpy(params.mapped, info.data(), sizeof(info));
    for (uint32_t i = 0; i < texels; ++i) static_cast<uint32_t*>(input.mapped)[i] = i * 0x9e3779b9u ^ 0xa57e31d2u;
    const VkDescriptorSetLayoutBinding bindings[] = {
        {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr},
        {1, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr},
        {2, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1, VK_SHADER_STAGE_COMPUTE_BIT, nullptr}};
    VkDescriptorSetLayoutCreateInfo set_info{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
    set_info.bindingCount = 3; set_info.pBindings = bindings;
    VkDescriptorSetLayout set_layout;
    Check(vkCreateDescriptorSetLayout(device, &set_info, nullptr, &set_layout));
    const VkPushConstantRange push{VK_SHADER_STAGE_COMPUTE_BIT, 0, 4};
    VkPipelineLayoutCreateInfo layout_info{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
    layout_info.setLayoutCount = 1; layout_info.pSetLayouts = &set_layout;
    layout_info.pushConstantRangeCount = 1; layout_info.pPushConstantRanges = &push;
    VkPipelineLayout layout;
    Check(vkCreatePipelineLayout(device, &layout_info, nullptr, &layout));
    VkShaderModuleCreateInfo module_info{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
    module_info.codeSize = sizeof(TILING_MICRO_32_COMP); module_info.pCode = TILING_MICRO_32_COMP;
    VkShaderModule module;
    Check(vkCreateShaderModule(device, &module_info, nullptr, &module));
    VkPipeline pipelines[2];
    for (uint32_t tiler = 0; tiler < 2; ++tiler) {
        const VkSpecializationMapEntry entry{3, 0, 4};
        const VkSpecializationInfo specialization{1, &entry, 4, &tiler};
        VkComputePipelineCreateInfo pipeline{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        pipeline.layout = layout;
        pipeline.stage = {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, nullptr, 0,
                          VK_SHADER_STAGE_COMPUTE_BIT, module, "main", &specialization};
        Check(vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &pipeline, nullptr, &pipelines[tiler]));
    }
    const VkDescriptorPoolSize sizes[] = {{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 4}, {VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 2}};
    VkDescriptorPoolCreateInfo pool_info{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
    pool_info.maxSets = 2; pool_info.poolSizeCount = 2; pool_info.pPoolSizes = sizes;
    VkDescriptorPool pool;
    Check(vkCreateDescriptorPool(device, &pool_info, nullptr, &pool));
    const VkDescriptorSetLayout layouts[] = {set_layout, set_layout};
    VkDescriptorSetAllocateInfo sets_info{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
    sets_info.descriptorPool = pool; sets_info.descriptorSetCount = 2; sets_info.pSetLayouts = layouts;
    VkDescriptorSet sets[2];
    Check(vkAllocateDescriptorSets(device, &sets_info, sets));
    for (uint32_t i = 0; i < 2; ++i) {
        VkDescriptorBufferInfo buffers[] = {{tiled.handle, 0, bytes},
            {i ? input.handle : output.handle, 0, bytes}, {params.handle, 0, 12 + 16 * 16}};
        VkWriteDescriptorSet writes[3]{};
        for (uint32_t j = 0; j < 3; ++j) {
            writes[j].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
            writes[j].dstSet = sets[i]; writes[j].dstBinding = j; writes[j].descriptorCount = 1;
            writes[j].descriptorType = j == 2 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER : VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            writes[j].pBufferInfo = &buffers[j];
        }
        vkUpdateDescriptorSets(device, 3, writes, 0, nullptr);
    }
    VkCommandPoolCreateInfo command_pool_info{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
    command_pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT; command_pool_info.queueFamilyIndex = family;
    VkCommandPool command_pool;
    Check(vkCreateCommandPool(device, &command_pool_info, nullptr, &command_pool));
    VkCommandBufferAllocateInfo command_info{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
    command_info.commandPool = command_pool; command_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; command_info.commandBufferCount = 1;
    VkCommandBuffer command;
    Check(vkAllocateCommandBuffers(device, &command_info, &command));
    for (uint32_t limit : {1u, 7u, 65536u}) {
        std::memset(tiled.mapped, 0xcc, bytes); std::memset(output.mapped, 0xdd, bytes);
        Check(vkResetCommandBuffer(command, 0));
        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        Check(vkBeginCommandBuffer(command, &begin));
        for (uint32_t pass : {1u, 0u}) {
            vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_COMPUTE, pipelines[pass]);
            vkCmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 0, 1, &sets[pass], 0, nullptr);
            assert(VideoCore::ForEachTilingDispatch(texels / 64, limit, [&](uint32_t base, uint32_t count) {
                vkCmdPushConstants(command, layout, VK_SHADER_STAGE_COMPUTE_BIT, 0, 4, &base);
                vkCmdDispatch(command, count, 1, 1);
            }));
            VkMemoryBarrier barrier{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
            barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
            barrier.dstAccessMask = pass ? VK_ACCESS_SHADER_READ_BIT : VK_ACCESS_HOST_READ_BIT;
            vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                pass ? VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT : VK_PIPELINE_STAGE_HOST_BIT, 0, 1, &barrier, 0, nullptr, 0, nullptr);
        }
        Check(vkEndCommandBuffer(command));
        VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
        submit.commandBufferCount = 1; submit.pCommandBuffers = &command;
        Check(vkQueueSubmit(queue, 1, &submit, VK_NULL_HANDLE));
        Check(vkQueueWaitIdle(queue));
        if (std::memcmp(input.mapped, output.mapped, bytes) != 0) throw std::runtime_error("Tiling round trip changed texels");
        std::printf("PASS: %u texels round trip exactly with batch limit %u\n", texels, limit);
    }
    vkDestroyCommandPool(device, command_pool, nullptr);
    vkDestroyDescriptorPool(device, pool, nullptr);
    for (auto pipeline : pipelines) vkDestroyPipeline(device, pipeline, nullptr);
    vkDestroyShaderModule(device, module, nullptr);
    vkDestroyPipelineLayout(device, layout, nullptr);
    vkDestroyDescriptorSetLayout(device, set_layout, nullptr);
    for (const auto buffer : {tiled, input, output, params}) {
        vkUnmapMemory(device, buffer.memory); vkDestroyBuffer(device, buffer.handle, nullptr); vkFreeMemory(device, buffer.memory, nullptr);
    }
    vkDestroyDevice(device, nullptr); vkDestroyInstance(instance, nullptr);
    return 0;
} catch (const std::exception& error) {
    std::fprintf(stderr, "FAIL: %s\n", error.what());
    return 1;
}
