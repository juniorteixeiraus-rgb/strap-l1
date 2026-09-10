// strap-pouw: C++ Proof-of-Useful-Work verification library
// Verifies proofs submitted by users who performed real-world activities
// Uses OpenSSL SHA256 (compatible with OpenSSL 3.x)

#include <openssl/sha.h>
#include <cstdint>
#include <cstring>

// IMPORTANT: this struct must match the Rust #[repr(C)] Proof in src/main.rs EXACTLY.
// Verified Rust layout via std::mem::offset_of / size_of probe:
//   sizeof(Proof)    = 160
//   alignof(Proof)   = 8
//   offsetof(proof_type)     = 0
//   offsetof(worker_id)      = 1   (1 byte + 31 bytes padding to align next u64)
//   offsetof(activity_hash)  = 33  (32 bytes + 31 bytes padding to align next u64)
//   offsetof(timestamp)      = 72  (u64, already 8-aligned)
//   offsetof(nonce)          = 80  (u64)
//   offsetof(metadata)       = 88  (u8[64])
//   offsetof(metadata_len)   = 152 (u8 at the end, struct padded to 160 total)

struct Proof {
    uint8_t     proof_type;        // offset 0,  size 1
    uint8_t     worker_id[32];     // offset 1,  size 32
    uint8_t     activity_hash[32]; // offset 33, size 32
    uint64_t    timestamp;         // offset 72, size 8
    uint64_t    nonce;             // offset 80, size 8
    uint8_t     metadata[64];      // offset 88, size 64
    uint8_t     metadata_len;      // offset 152, size 1
}; // total 160 bytes (padded to multiple of alignment 8)

static_assert(sizeof(Proof) == 160,
              "Proof struct must be 160 bytes to match Rust repr(C) layout");

extern "C" {

bool strap_verify_proof(const Proof* proof, uint8_t difficulty) {
    if (!proof || difficulty > 32) return false;
    uint8_t hash[32];
    SHA256(reinterpret_cast<const unsigned char*>(proof), sizeof(Proof), hash);
    for (uint8_t i = 0; i < difficulty && i < 32; ++i) {
        if (hash[i] != 0) return false;
    }
    return true;
}

uint64_t strap_mine_proof(Proof* proof, uint8_t difficulty, uint64_t max_attempts) {
    if (!proof || max_attempts == 0) return 0;
    for (uint64_t n = 1; n <= max_attempts; ++n) {
        proof->nonce = n;
        uint8_t hash[32];
        SHA256(reinterpret_cast<const unsigned char*>(proof), sizeof(Proof), hash);
        bool ok = true;
        for (uint8_t i = 0; i < difficulty && i < 32; ++i) {
            if (hash[i] != 0) { ok = false; break; }
        }
        if (ok) return n;
    }
    return 0;
}

void strap_compute_proof_hash(const Proof* proof, uint8_t* out) {
    if (!proof || !out) return;
    SHA256(reinterpret_cast<const unsigned char*>(proof), sizeof(Proof), out);
}

} // extern "C"
