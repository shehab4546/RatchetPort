// Hook sites found by signature (src/signature.h): in the reference eboot.bin and in a build whose
// code moved, as the full 01.02 update's does (+0x120 in one region, -0x10 in another).
#include <cassert>
#include <cstdio>
#include <vector>
#include <cstring>
#include "../src/signature.h"


static uint64_t Find(const std::vector<unsigned char>& image, const SpartanSignature& sig) {
    return spartanport_signature_find(image.data(), image.size(), &sig);
}

int main(int argc, char** argv) {
    int parsed[RATCHET_SIGNATURE_MAX];
    assert(spartanport_signature_parse("c5 ?? 0a", parsed) == 3 && parsed[0] == 0xc5 && parsed[1] == -1 && parsed[2] == 10);
    assert(!spartanport_signature_parse("c5 g0", parsed) && !spartanport_signature_parse("c5 0", parsed));

    std::vector<unsigned char> buffer(256);
    const unsigned char bytes[] = {0x48, 0x8d, 0x05, 1, 2, 3, 4, 0xc3};
    const SpartanSignature sig = {"48 8d 05 ?? ?? ?? ?? c3", 3};
    assert(Find(buffer, sig) == UINT64_MAX);                       // absent
    memcpy(buffer.data() + 100, bytes, sizeof(bytes));
    assert(Find(buffer, sig) == 103);                              // the site, wildcards ignored
    buffer[103] = 9;
    assert(Find(buffer, sig) == 103);
    memcpy(buffer.data() + 200, bytes, sizeof(bytes));
    assert(Find(buffer, sig) == UINT64_MAX);                       // twice: ambiguous
    memcpy(buffer.data() + 248, bytes, sizeof(bytes));             // a match at the very end counts
    buffer[200] = 0;
    assert(Find(buffer, sig) == UINT64_MAX);
    buffer[100] = 0;
    assert(Find(buffer, sig) == 251);

    (void)argc;
    (void)argv;
    std::puts("signatures-test: OK");
    return 0;
}
