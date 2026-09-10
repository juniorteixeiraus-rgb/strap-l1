// strap_l1::ffi — Rust FFI bindings to C++ PoUW verifier

use std::os::raw::c_char;

/// Matches C++ ProofInput
#[repr(C)]
pub struct ProofInput {
    pub worker_id:     [u8; 32],
    pub activity_hash: [u8; 32],
    pub nonce:         u64,
    pub checksum:      u64,
    pub timestamp:     u64,
    pub proof_type:    u8,   // 0=ComputeWork, 1=PhysicalActivity, 2=DataValidation, 3=CommunityTask
    pub metadata_len:  u8,
    pub metadata:      *const u8,
}

#[repr(C)]
pub struct ProofResult {
    pub proof_hash: [u8; 32],
    pub valid:      bool,
    pub tries:      u64,
}

extern "C" {
    /// Returns 1 if valid, 0 if invalid.
    pub fn strap_verify_proof(inp: *const ProofInput, out: *mut ProofResult) -> i32;
}

/// Call the C++ verifier. Returns the result or an error string.
pub fn verify_proof(inp: &ProofInput) -> Result<ProofResult, String> {
    let mut out = ProofResult {
        proof_hash: [0u8; 32],
        valid: false,
        tries: 0,
    };
    let ret = unsafe {
        strap_verify_proof(
            inp as *const ProofInput,
            &mut out as *mut ProofResult,
        )
    };
    if ret == 0 {
        Err(format!("Proof verification failed at nonce {}", inp.nonce))
    } else {
        Ok(out)
    }
}
