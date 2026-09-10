// strap-pouw: C++ Proof-of-Useful-Work verification library
// Verifies proofs submitted by users who performed real-world activities

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <random>
#include <chrono>
#include <openssl/sha.h>

extern "C" {

// Proof types supported by Strap
enum ProofType : uint8_t {
    ProofType_ComputeWork = 0,
    ProofType_PhysicalActivity = 1,
    ProofType_DataValidation = 2,
    ProofType_CreativeWork = 3,
};

// A proof submitted by a user
struct Proof {
    uint8_t type;
    uint8_t worker_id[32];
    uint8_t activity_hash[32];
    uint64_t timestamp;
    uint64_t nonce;
    uint8_t metadata[64];
    uint8_t metadata_len;
};

// Verify a proof: returns true if proof is valid
extern bool strap_verify_proof(const Proof* proof, uint8_t difficulty) {
    if (!proof) return false;
    
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256_CTX ctx;
    SHA256_Init(&ctx);
    
    SHA256_Update(&ctx, &proof->type, 1);
    SHA256_Update(&ctx, proof->worker_id, 32);
    SHA256_Update(&ctx, proof->activity_hash, 32);
    SHA256_Update(&ctx, &proof->timestamp, sizeof(uint64_t));
    SHA256_Update(&ctx, &proof->nonce, sizeof(uint64_t));
    if (proof->metadata_len > 0) {
        SHA256_Update(&ctx, proof->metadata, proof->metadata_len);
    }
    
    SHA256_Final(hash, &ctx);
    
    for (uint8_t i = 0; i < difficulty && i < 32; i++) {
        if (hash[i] != 0) return false;
    }
    
    return true;
}

// Mine a proof by finding a valid nonce
extern uint64_t strap_mine_proof(Proof* proof, uint8_t difficulty, uint64_t max_attempts) {
    if (!proof) return 0;
    
    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    unsigned char hash[SHA256_DIGEST_LENGTH];
    
    for (uint64_t attempt = 0; attempt < max_attempts; attempt++) {
        proof->nonce = rng();
        
        SHA256_CTX ctx;
        SHA256_Init(&ctx);
        SHA256_Update(&ctx, &proof->type, 1);
        SHA256_Update(&ctx, proof->worker_id, 32);
        SHA256_Update(&ctx, proof->activity_hash, 32);
        SHA256_Update(&ctx, &proof->timestamp, sizeof(uint64_t));
        SHA256_Update(&ctx, &proof->nonce, sizeof(uint64_t));
        if (proof->metadata_len > 0) {
            SHA256_Update(&ctx, proof->metadata, proof->metadata_len);
        }
        SHA256_Final(hash, &ctx);
        
        bool valid = true;
        for (uint8_t i = 0; i < difficulty && i < 32; i++) {
            if (hash[i] != 0) { valid = false; break; }
        }
        
        if (valid) return proof->nonce;
    }
    
    return 0;
}

// Compute proof hash
extern void strap_compute_proof_hash(const Proof* proof, uint8_t* out) {
    if (!proof || !out) return;
    
    SHA256_CTX ctx;
    SHA256_Init(&ctx);
    SHA256_Update(&ctx, &proof->type, 1);
    SHA256_Update(&ctx, proof->worker_id, 32);
    SHA256_Update(&ctx, proof->activity_hash, 32);
    SHA256_Update(&ctx, &proof->timestamp, sizeof(uint64_t));
    SHA256_Update(&ctx, &proof->nonce, sizeof(uint64_t));
    if (proof->metadata_len > 0) {
        SHA256_Update(&ctx, proof->metadata, proof->metadata_len);
    }
    SHA256_Final(out, &ctx);
}

// Create a physical activity proof from sensor data
extern void strap_create_physical_proof(
    Proof* proof,
    const uint8_t* worker_id,
    const uint8_t* sensor_data,
    size_t sensor_len,
    const char* activity_desc
) {
    if (!proof || !worker_id || !sensor_data || sensor_len == 0) return;
    
    proof->type = ProofType_PhysicalActivity;
    memcpy(proof->worker_id, worker_id, 32);
    proof->timestamp = std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()
    ).count();
    proof->nonce = 0;
    
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256_CTX ctx;
    SHA256_Init(&ctx);
    SHA256_Update(&ctx, sensor_data, sensor_len);
    SHA256_Update(&ctx, activity_desc, strlen(activity_desc));
    SHA256_Final(hash, &ctx);
    memcpy(proof->activity_hash, hash, 32);
    
    size_t desc_len = strlen(activity_desc);
    if (desc_len > 63) desc_len = 63;
    memcpy(proof->metadata, activity_desc, desc_len);
    proof->metadata_len = (uint8_t)desc_len;
}

} // extern "C"
