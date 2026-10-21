/* PlayGo header layout: shadPS4 src/core/file_format/playgo_chunk.h.
 * Validate every range before trusting chunk_count. No game data is embedded. */
#ifndef RATCHET_PLAYGO_METADATA_H
#define RATCHET_PLAYGO_METADATA_H
#include <stdint.h>
#include <stddef.h>
#define PLAYGO_HEADER_SIZE 256
#define PLAYGO_MAX_CHUNKS 1000
static uint16_t pg_u16(const unsigned char *p) { return (uint16_t)(p[0] | (uint16_t)p[1]<<8); }
static uint32_t pg_u32(const unsigned char *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static int playgo_metadata_chunks(const unsigned char *h, size_t bytes, uint64_t file_size) {
    if (bytes != PLAYGO_HEADER_SIZE || file_size < PLAYGO_HEADER_SIZE ||
        pg_u32(h) != UINT32_C(0x6f676c70) || pg_u32(h+16) != file_size) return -1;
    unsigned chunks=pg_u16(h+10), mchunks=pg_u16(h+12), scenarios=pg_u16(h+14);
    if (!chunks || chunks>PLAYGO_MAX_CHUNKS || mchunks>8000 || scenarios>32 ||
        (scenarios && pg_u16(h+20)>=scenarios)) return -1;
    uint32_t offsets[8], lengths[8];
    for (unsigned i=0;i<8;++i) {
        offsets[i]=pg_u32(h+192+8*i); lengths[i]=pg_u32(h+196+8*i);
        if (offsets[i]>file_size || lengths[i]>file_size-offsets[i] ||
            (lengths[i] && offsets[i]<PLAYGO_HEADER_SIZE)) return -1;
        for (unsigned j=0;j<i;++j)
            if (lengths[i] && lengths[j] && offsets[i]<(uint64_t)offsets[j]+lengths[j] &&
                offsets[j]<(uint64_t)offsets[i]+lengths[i]) return -1;
    }
    if (lengths[0]<chunks*32 || lengths[0]%32 || lengths[1]%2 ||
        lengths[3]<mchunks*16 || lengths[3]%16 || lengths[4]<scenarios*32 ||
        lengths[4]%32 || lengths[5]%2 || lengths[7]%16) return -1;
    return (int)chunks;
}
#endif
