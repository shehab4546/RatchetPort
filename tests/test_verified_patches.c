// SPDX-License-Identifier: GPL-2.0-or-later
#include "../src/verified_patches.h"
#include <assert.h>

static void put64(unsigned char *p, uint64_t x) {
    for (int i = 0; i < 8; ++i) p[i] = (unsigned char)(x >> (8 * i));
}
static const char *range(uint64_t a, uint64_t n, void *context) {
    (void)context;
    if (a + n > 24) return "outside segment";
    if (rp_overlap(a, n, 16, 4)) return "reserved transformation";
    return NULL;
}
static size_t packet(unsigned char *p, const unsigned char *image) {
    memset(p, 0, 128);
    memcpy(p, "RCPATCH3", 8); put64(p + 8, 32);
    ratchet_sha256(image, 32, p + 16); memset(p + 48, 42, 16); put64(p + 64, 2);
    put64(p + 72, 2); put64(p + 80, 2); memcpy(p + 88, image + 2, 2); memset(p + 90, 90, 2);
    put64(p + 92, 10); put64(p + 100, 2); memcpy(p + 108, image + 10, 2); memset(p + 110, 91, 2);
    return 112;
}
static void rejected(unsigned char *p, size_t bytes, unsigned char *image) {
    unsigned char before[32]; memcpy(before, image, 32);
    RpPlan plan;
    assert(rp_parse(&plan, p, bytes, image, 32, range, NULL));
    assert(!memcmp(before, image, 32));
    rp_free(&plan);
}
/* Cross-language transport harness used by test_ratchet_patches.py. */
static int transport(int argc, char **argv) {
    if (argc != 5) return 2;
    unsigned char image[32]; FILE *f = fopen(argv[1], "rb");
    if (!f || fread(image, 1, 32, f) != 32) return 3;
    fclose(f);
    RpPlan plan;
    const char *error = rp_load(&plan, argv[2], image, 32, range, NULL);
    if (!error) error = rp_apply(&plan, image);
    if (!error) error = rp_receipt(&plan, argv[3]);
    rp_free(&plan);
    if (error) { fprintf(stderr, "%s\n", error); return 4; }
    f = fopen(argv[4], "wb");
    if (!f) return 5;
    int bad = fwrite(image, 1, 32, f) != 32;
    if (fclose(f)) bad = 1;
    return bad ? 5 : 0;
}
int main(int argc, char **argv) {
    if (argc != 1) return transport(argc, argv);
    unsigned char image[32], raw[128], fresh[32];
    for (int i = 0; i < 32; ++i) image[i] = (unsigned char)i;
    memcpy(fresh, image, 32);
    size_t bytes = packet(raw, image);
    RpPlan plan;
    assert(!rp_parse(&plan, raw, bytes, image, 32, range, NULL));
    assert(!memcmp(image, fresh, 32)); /* Parsing never writes. */
    image[10] ^= 1; /* A late failure in the second write must leave the first untouched. */
    assert(rp_apply(&plan, image));
    assert(image[2] == 2 && image[3] == 3);
    image[10] ^= 1;
    assert(!rp_apply(&plan, image));
    assert(image[2] == 90 && image[3] == 90 && image[10] == 91 && image[11] == 91);
    assert(image[1] == 1 && image[4] == 4 && image[12] == 12);
    rp_free(&plan); memcpy(image, fresh, 32);
    /* Every truncated prefix, plus trailing data, must reject without writes. */
    for (size_t n = 0; n < bytes; ++n) rejected(raw, n, image);
    rejected(raw, bytes + 1, image);
    packet(raw, image); raw[16] ^= 1; rejected(raw, bytes, image);
    packet(raw, image); put64(raw + 8, 31); rejected(raw, bytes, image);
    packet(raw, image); put64(raw + 64, RP_MAX_WRITES + 1); rejected(raw, bytes, image);
    packet(raw, image); raw[108] ^= 1; rejected(raw, bytes, image);
    packet(raw, image); put64(raw + 92, 3); rejected(raw, bytes, image);
    packet(raw, image); put64(raw + 92, UINT64_MAX); rejected(raw, bytes, image);
    packet(raw, image); put64(raw + 100, RP_MAX_BYTES + 1); rejected(raw, bytes, image);
    packet(raw, image); put64(raw + 100, 0); rejected(raw, bytes, image);
    packet(raw, image); put64(raw + 92, 24); memcpy(raw + 108, image + 24, 2); rejected(raw, bytes, image);
    packet(raw, image); put64(raw + 92, 16); memcpy(raw + 108, image + 16, 2); rejected(raw, bytes, image);
    packet(raw, image); memcpy(raw + 110, raw + 108, 2); rejected(raw, bytes, image);
    memset(raw, 0, sizeof(raw)); memcpy(raw, "G3PATCH2", 8); put64(raw + 16, 1); rejected(raw, 24, image);
    put64(raw + 16, 0); assert(!rp_parse(&plan, raw, 24, image, 32, range, NULL)); rp_free(&plan);
    memset(raw, 0, sizeof(raw)); memcpy(raw, "RCPATCH3", 8);
    assert(!rp_parse(&plan, raw, RP_HEADER, image, 32, range, NULL));
    assert(!rp_apply(&plan, image)); assert(!memcmp(image, fresh, 32)); rp_free(&plan);
    raw[8] = 1; rejected(raw, RP_HEADER, image);
    /* Known answer, independent of packet generation. */
    unsigned char hash[32];
    const unsigned char abc[32] = {0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
        0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
    ratchet_sha256((const unsigned char *)"abc", 3, hash); assert(!memcmp(hash, abc, 32));
    puts("Verified patch transactions: passed");
    return 0;
}
