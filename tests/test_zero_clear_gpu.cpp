// Execute the captured Ratchet zero shader on Vulkan. Compare subsequent buffer->image
// conversion with a typed native clear, and verify the shader's raw buffer + guard bytes.
#include <vulkan/vulkan.h>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <vector>
static void Check(VkResult r) { if(r!=VK_SUCCESS) throw std::runtime_error("Vulkan result "+std::to_string(r)); }
struct Buffer { VkBuffer handle; VkDeviceMemory memory; void* data; };
struct Image { VkImage handle; VkDeviceMemory memory; };
int main(int argc,char** argv) try {
    if(argc!=2) throw std::runtime_error("Pass captured cs_0540709a SPIR-V path");
    std::ifstream file(argv[1],std::ios::binary|std::ios::ate);
    if(!file) throw std::runtime_error("Missing captured shader");
    auto size=static_cast<std::size_t>(file.tellg());
    std::vector<uint32_t> code(size/4); file.seekg(0); file.read(reinterpret_cast<char*>(code.data()),size);
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO}; app.apiVersion=VK_API_VERSION_1_3;
    VkInstanceCreateInfo ic{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO}; ic.pApplicationInfo=&app;
    VkInstance instance; Check(vkCreateInstance(&ic,nullptr,&instance));
    uint32_t count=1; VkPhysicalDevice physical; Check(vkEnumeratePhysicalDevices(instance,&count,&physical));
    uint32_t fc=0; vkGetPhysicalDeviceQueueFamilyProperties(physical,&fc,nullptr);
    std::vector<VkQueueFamilyProperties> families(fc); vkGetPhysicalDeviceQueueFamilyProperties(physical,&fc,families.data());
    uint32_t family=0; while(family<fc && !(families[family].queueFlags&VK_QUEUE_GRAPHICS_BIT)) ++family;
    if(family==fc) throw std::runtime_error("No graphics/compute queue");
    float priority=1; VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
    qi.queueFamilyIndex=family; qi.queueCount=1; qi.pQueuePriorities=&priority;
    VkPhysicalDeviceVulkan12Features f12{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES};
    f12.storageBuffer8BitAccess=VK_TRUE; f12.shaderInt8=VK_TRUE;
    VkPhysicalDeviceVulkan11Features f11{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_1_FEATURES};
    f11.pNext=&f12; f11.storageBuffer16BitAccess=VK_TRUE;
    VkPhysicalDeviceFeatures features{}; features.shaderInt64=VK_TRUE; features.shaderInt16=VK_TRUE;
    VkDeviceCreateInfo dc{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO}; dc.pNext=&f11;
    dc.pEnabledFeatures=&features; dc.queueCreateInfoCount=1; dc.pQueueCreateInfos=&qi;
    VkDevice device; Check(vkCreateDevice(physical,&dc,nullptr,&device));
    VkQueue queue; vkGetDeviceQueue(device,family,0,&queue);
    VkPhysicalDeviceMemoryProperties mp; vkGetPhysicalDeviceMemoryProperties(physical,&mp);
    const auto allocate=[&](VkMemoryRequirements req,VkMemoryPropertyFlags flags) {
        uint32_t type=0; while(type<mp.memoryTypeCount && (!(req.memoryTypeBits&(1u<<type)) ||
             (mp.memoryTypes[type].propertyFlags&flags)!=flags)) ++type;
        if(type==mp.memoryTypeCount) throw std::runtime_error("No memory type");
        VkMemoryAllocateInfo a{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO}; a.allocationSize=req.size; a.memoryTypeIndex=type;
        VkDeviceMemory memory; Check(vkAllocateMemory(device,&a,nullptr,&memory)); return memory;
    };
    const auto buffer=[&](VkDeviceSize bytes,VkBufferUsageFlags usage) {
        Buffer b{}; VkBufferCreateInfo c{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO}; c.size=bytes; c.usage=usage;
        Check(vkCreateBuffer(device,&c,nullptr,&b.handle)); VkMemoryRequirements req;
        vkGetBufferMemoryRequirements(device,b.handle,&req); b.memory=allocate(req,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        Check(vkBindBufferMemory(device,b.handle,b.memory,0)); Check(vkMapMemory(device,b.memory,0,bytes,0,&b.data)); return b;
    };
    VkDescriptorSetLayoutBinding binding{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr};
    VkDescriptorSetLayoutCreateInfo sc{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO}; sc.bindingCount=1; sc.pBindings=&binding;
    VkDescriptorSetLayout sl; Check(vkCreateDescriptorSetLayout(device,&sc,nullptr,&sl));
    VkPushConstantRange push{VK_SHADER_STAGE_COMPUTE_BIT,0,128};
    VkPipelineLayoutCreateInfo lc{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO}; lc.setLayoutCount=1; lc.pSetLayouts=&sl;
    lc.pushConstantRangeCount=1; lc.pPushConstantRanges=&push;
    VkPipelineLayout layout; Check(vkCreatePipelineLayout(device,&lc,nullptr,&layout));
    VkShaderModuleCreateInfo mc{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO}; mc.codeSize=size; mc.pCode=code.data();
    VkShaderModule module; Check(vkCreateShaderModule(device,&mc,nullptr,&module));
    VkComputePipelineCreateInfo pc{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO}; pc.layout=layout;
    pc.stage={VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,nullptr,0,VK_SHADER_STAGE_COMPUTE_BIT,module,"main",nullptr};
    VkPipeline pipeline; Check(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&pc,nullptr,&pipeline));
    VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1};
    VkDescriptorPoolCreateInfo dpc{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO}; dpc.maxSets=1; dpc.poolSizeCount=1; dpc.pPoolSizes=&ps;
    VkDescriptorPool dp; Check(vkCreateDescriptorPool(device,&dpc,nullptr,&dp));
    VkDescriptorSetAllocateInfo sa{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO}; sa.descriptorPool=dp; sa.descriptorSetCount=1; sa.pSetLayouts=&sl;
    VkDescriptorSet set; Check(vkAllocateDescriptorSets(device,&sa,&set));
    VkCommandPoolCreateInfo cc{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO}; cc.queueFamilyIndex=family; cc.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    VkCommandPool cp; Check(vkCreateCommandPool(device,&cc,nullptr,&cp));
    VkCommandBufferAllocateInfo ca{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO}; ca.commandPool=cp; ca.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY; ca.commandBufferCount=1;
    VkCommandBuffer cmd; Check(vkAllocateCommandBuffers(device,&ca,&cmd));
    struct Case {uint32_t width,height,pitch,bytes; VkFormat format;};
    for(auto c:std::array{Case{1920,1080,1920,8355840,VK_FORMAT_R8G8B8A8_UNORM},
                         Case{960,540,1024,2359296,VK_FORMAT_B10G11R11_UFLOAT_PACK32}}) {
        auto raw=buffer(c.bytes+1024,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT|VK_BUFFER_USAGE_TRANSFER_SRC_BIT);
        auto read=buffer(uint64_t(c.width)*c.height*8,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
        std::memset(raw.data,0xa5,c.bytes+1024); std::memset(read.data,0xdd,uint64_t(c.width)*c.height*8);
        std::array<Image,2> images{};
        for(auto& i:images) {
            VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO}; ci.imageType=VK_IMAGE_TYPE_2D; ci.format=c.format;
            ci.extent={c.width,c.height,1}; ci.mipLevels=1; ci.arrayLayers=1; ci.samples=VK_SAMPLE_COUNT_1_BIT;
            ci.tiling=VK_IMAGE_TILING_OPTIMAL; ci.usage=VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT;
            Check(vkCreateImage(device,&ci,nullptr,&i.handle)); VkMemoryRequirements req; vkGetImageMemoryRequirements(device,i.handle,&req);
            i.memory=allocate(req,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT); Check(vkBindImageMemory(device,i.handle,i.memory,0));
        }
        VkDescriptorBufferInfo bi{raw.handle,0,c.bytes}; VkWriteDescriptorSet write{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
        write.dstSet=set; write.descriptorCount=1; write.descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; write.pBufferInfo=&bi;
        vkUpdateDescriptorSets(device,1,&write,0,nullptr);
        Check(vkResetCommandBuffer(cmd,0)); VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO}; Check(vkBeginCommandBuffer(cmd,&begin));
        vkCmdBindPipeline(cmd,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);
        vkCmdBindDescriptorSets(cmd,VK_PIPELINE_BIND_POINT_COMPUTE,layout,0,1,&set,0,nullptr);
        const std::array<uint32_t,32> zeros{}; vkCmdPushConstants(cmd,layout,VK_SHADER_STAGE_COMPUTE_BIT,0,128,zeros.data());
        vkCmdDispatch(cmd,c.bytes/1024,1,1);
        VkMemoryBarrier barrier{VK_STRUCTURE_TYPE_MEMORY_BARRIER}; barrier.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;
        barrier.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT|VK_ACCESS_HOST_READ_BIT;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT|VK_PIPELINE_STAGE_HOST_BIT,0,1,&barrier,0,nullptr,0,nullptr);
        for(auto i:images) {
            VkImageMemoryBarrier ib{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER}; ib.oldLayout=VK_IMAGE_LAYOUT_UNDEFINED; ib.newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
            ib.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT; ib.srcQueueFamilyIndex=ib.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
            ib.image=i.handle; ib.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
            vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&ib);
            VkClearColorValue dirty{}; dirty.float32[0]=1; vkCmdClearColorImage(cmd,i.handle,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&dirty,1,&ib.subresourceRange);
        }
        VkMemoryBarrier writes{VK_STRUCTURE_TYPE_MEMORY_BARRIER}; writes.srcAccessMask=writes.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,1,&writes,0,nullptr,0,nullptr);
        VkBufferImageCopy copy{}; copy.bufferRowLength=c.pitch; copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1}; copy.imageExtent={c.width,c.height,1};
        vkCmdCopyBufferToImage(cmd,raw.handle,images[0].handle,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,1,&copy);
        VkClearColorValue clear{}; VkImageSubresourceRange range{VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        vkCmdClearColorImage(cmd,images[1].handle,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&clear,1,&range);
        for(unsigned n=0;n<images.size();++n) {
            VkImageMemoryBarrier ib{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER}; ib.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL; ib.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
            ib.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT; ib.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
            ib.srcQueueFamilyIndex=ib.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED; ib.image=images[n].handle; ib.subresourceRange=range;
            vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&ib);
            copy.bufferOffset=uint64_t(n)*c.width*c.height*4; copy.bufferRowLength=0;
            vkCmdCopyImageToBuffer(cmd,images[n].handle,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,read.handle,1,&copy);
        }
        writes.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT; writes.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&writes,0,nullptr,0,nullptr);
        Check(vkEndCommandBuffer(cmd)); VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO}; submit.commandBufferCount=1; submit.pCommandBuffers=&cmd;
        Check(vkQueueSubmit(queue,1,&submit,VK_NULL_HANDLE)); Check(vkQueueWaitIdle(queue));
        const auto* bytes=static_cast<const uint8_t*>(raw.data);
        for(uint32_t n=0;n<c.bytes;++n) if(bytes[n]) throw std::runtime_error("Original shader left nonzero raw bytes");
        for(uint32_t n=c.bytes;n<c.bytes+1024;++n) if(bytes[n]!=0xa5) throw std::runtime_error("Original shader overran descriptor");
        const auto payload=uint64_t(c.width)*c.height*4;
        if(std::memcmp(read.data,static_cast<uint8_t*>(read.data)+payload,payload)) throw std::runtime_error("Clear differs from buffer conversion");
        for(uint64_t n=0;n<payload*2;++n) if(static_cast<uint8_t*>(read.data)[n]) throw std::runtime_error("Nonzero image texel");
        std::printf("PASS: captured zero shader %ux%u fmt=%u raw=%u guard=1024; copy and clear match every texel\n",c.width,c.height,c.format,c.bytes);
        for(auto i:images) {vkDestroyImage(device,i.handle,nullptr);vkFreeMemory(device,i.memory,nullptr);}
        for(auto b:{raw,read}) {vkUnmapMemory(device,b.memory);vkDestroyBuffer(device,b.handle,nullptr);vkFreeMemory(device,b.memory,nullptr);}
    }
    vkDestroyCommandPool(device,cp,nullptr); vkDestroyDescriptorPool(device,dp,nullptr); vkDestroyPipeline(device,pipeline,nullptr);
    vkDestroyShaderModule(device,module,nullptr); vkDestroyPipelineLayout(device,layout,nullptr); vkDestroyDescriptorSetLayout(device,sl,nullptr);
    vkDestroyDevice(device,nullptr);vkDestroyInstance(instance,nullptr);
} catch(const std::exception& error) {std::fprintf(stderr,"FAIL: %s\n",error.what());return 1;}
