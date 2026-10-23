// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef RATCHET_VERIFIED_PATCHES_H
#define RATCHET_VERIFIED_PATCHES_H
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sha256.h"

/* RCPATCH3, little endian. All records validated before any guest write.
 * The caller's range check must exclude relocations and transformation sites. */
enum { RP_HEADER = 72, RP_MAX_WRITES = 1024, RP_MAX_BYTES = 4096,
       RP_MAX_PACKET = RP_HEADER + RP_MAX_WRITES * (16 + 2 * RP_MAX_BYTES) };
typedef struct { uint64_t address, length; const unsigned char *before, *after; } RpWrite;
typedef struct {
    unsigned char *packet;
    unsigned char token[16];
    uint64_t count;
    RpWrite writes[RP_MAX_WRITES];
} RpPlan;
typedef const char *(*RpRangeCheck)(uint64_t address, uint64_t length, void *context);

static inline uint64_t rp_u64(const unsigned char *p) {
    uint64_t value = 0;
    for (int i = 7; i >= 0; --i) value = (value << 8) | p[i];
    return value;
}
static inline void rp_free(RpPlan *p) { free(p->packet); memset(p, 0, sizeof(*p)); }
static inline int rp_overlap(uint64_t a, uint64_t n, uint64_t b, uint64_t m) {
    return a <= b ? b - a < n : a - b < m;
}
/* Parse an owned copy. The caller always rp_free()s the plan, including on error. */
static inline const char *rp_parse(RpPlan *p, const unsigned char *data, size_t bytes,
                                  const unsigned char *image, uint64_t size,
                                  RpRangeCheck check, void *context) {
    memset(p, 0, sizeof(*p));
    /* Only the empty legacy packet is allowed, for older direct-loader scripts. */
    if (bytes == 24 && !memcmp(data, "G3PATCH2", 8) && rp_u64(data + 16) == 0) return NULL;
    if (bytes < RP_HEADER || bytes > RP_MAX_PACKET || memcmp(data, "RCPATCH3", 8))
        return "invalid verified patch header (legacy writes are disabled)";
    p->count = rp_u64(data + 64);
    if (p->count > RP_MAX_WRITES) return "too many patch writes";
    memcpy(p->token, data + 48, 16);
    if (p->count) {
        unsigned char hash[32];
        if (rp_u64(data + 8) != size) return "patch image size mismatch";
        ratchet_sha256(image, size, hash);
        if (memcmp(hash, data + 16, 32)) return "patch image fingerprint mismatch";
    } else {
        unsigned char zero[40] = {0};
        if (memcmp(data + 8, zero, sizeof(zero))) return "invalid empty patch fingerprint";
    }
    p->packet = (unsigned char *)malloc(bytes);
    if (!p->packet) return "patch allocation failed";
    memcpy(p->packet, data, bytes);
    size_t at = RP_HEADER;
    uint64_t end = 0;
    for (uint64_t i = 0; i < p->count; ++i) {
        if (bytes - at < 16) return "truncated patch record";
        RpWrite *w = &p->writes[i];
        w->address = rp_u64(p->packet + at);
        w->length = rp_u64(p->packet + at + 8);
        at += 16;
        if (!w->length || w->length > RP_MAX_BYTES || w->address > size || w->length > size - w->address)
            return "patch write outside image bounds";
        if (i && w->address < end) return "unordered or overlapping patch writes";
        end = w->address + w->length;
        if (bytes - at < 2 * w->length) return "truncated patch bytes";
        w->before = p->packet + at;
        w->after = w->before + w->length;
        at += (size_t)(2 * w->length);
        if (!memcmp(w->before, w->after, (size_t)w->length)) return "unchanged patch write";
        if (memcmp(image + w->address, w->before, (size_t)w->length)) return "patch original bytes mismatch";
        const char *error = check ? check(w->address, w->length, context) : NULL;
        if (error) return error;
    }
    return at == bytes ? NULL : "trailing patch bytes";
}
static inline const char *rp_load(RpPlan *p, const char *path, const unsigned char *image,
                                 uint64_t size, RpRangeCheck check, void *context) {
    memset(p, 0, sizeof(*p));
    FILE *f = fopen(path, "rb");
    if (!f) return "cannot open verified patch packet";
    unsigned char *data = (unsigned char *)malloc(RP_MAX_PACKET + 1);
    if (!data) { fclose(f); return "patch allocation failed"; }
    size_t bytes = fread(data, 1, RP_MAX_PACKET + 1, f);
    int bad = ferror(f);
    fclose(f);
    const char *error = bad ? "cannot read patch packet" : rp_parse(p, data, bytes, image, size, check, context);
    free(data);
    return error;
}
/* Called after all loader transformations, while memory is still writable.
 * A late mismatch rejects the entire transaction, including earlier valid records. */
static inline const char *rp_apply(const RpPlan *p, unsigned char *image) {
    for (uint64_t i = 0; i < p->count; ++i) {
        const RpWrite *w = &p->writes[i];
        if (memcmp(image + w->address, w->before, (size_t)w->length))
            return "loader changed patch originals; transaction rejected";
    }
    for (uint64_t i = 0; i < p->count; ++i) {
        const RpWrite *w = &p->writes[i];
        memcpy(image + w->address, w->after, (size_t)w->length);
    }
    return NULL;
}
/* Receipt is published only once every write has been applied successfully. */
static inline const char *rp_receipt(const RpPlan *p, const char *path) {
    unsigned char data[32] = {0};
    memcpy(data, "RCPACK3", 7);
    memcpy(data + 8, p->token, 16);
    for (int i = 0; i < 8; ++i) data[24 + i] = (unsigned char)(p->count >> (8 * i));
    size_t len = strlen(path);
    char *tmp = (char *)malloc(len + 5);
    if (!tmp) return "receipt allocation failed";
    memcpy(tmp, path, len); memcpy(tmp + len, ".tmp", 5);
    FILE *f = fopen(tmp, "wb");
    int bad = !f;
    if (f) {
        bad = fwrite(data, 1, sizeof(data), f) != sizeof(data);
        if (fclose(f)) bad = 1;
    }
    if (!bad && rename(tmp, path)) bad = 1;
    if (bad) remove(tmp);
    free(tmp);
    return bad ? "cannot publish patch receipt" : NULL;
}
#endif
