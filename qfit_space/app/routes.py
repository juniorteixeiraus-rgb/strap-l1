"""QFit.space — Routes for the SaaS API"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

api = Blueprint('qfit', __name__)


@api.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "version": current_app.config.get('QFIT_VERSION', '1.0.0'),
        "network": current_app.config.get('QFIT_NETWORK', 'Strap 722'),
        "license": current_app.config.get('LICENSE_STATUS', 'inactive'),
        "llm_model": current_app.config.get('LLM_MODEL', 'llama3'),
        "timestamp": datetime.utcnow().isoformat(),
    })


@api.route('/chat', methods=['POST'])
def chat():
    """Send a message to the AI chatbot."""
    data = request.get_json()
    user_id = data.get('user_id', 'anonymous')
    message = data.get('message', '')
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    license_status = current_app.config.get('LICENSE_STATUS', 'inactive')
    if license_status != 'active':
        return jsonify({
            "error": "License not active. Purchase QFit.space for $799 to unlock.",
            "pricing": {"amount": 799, "currency": "USD", "type": "lifetime"}
        }), 403
    
    # Get conversation history
    conversation = current_app.conversations.get(user_id, [])
    
    # Build prompt with context
    prompt = build_prompt(message, conversation)
    
    # Get LLM response
    response = current_app.llm_engine.generate(prompt)
    
    # Store conversation
    conversation.append({"role": "user", "content": message})
    conversation.append({"role": "assistant", "content": response})
    current_app.conversations[user_id] = conversation[-20:]  # Keep last 20 messages
    
    return jsonify({
        "user_id": user_id,
        "response": response,
        "model": current_app.config.get('LLM_MODEL', 'llama3'),
        "timestamp": datetime.utcnow().isoformat(),
    })


@api.route('/license', methods=['GET'])
def get_license():
    """Get current license status."""
    return jsonify(current_app.config.get('LICENSE_INFO', {
        "status": "inactive",
        "message": "Purchase QFit.space for $799 to activate"
    }))


@api.route('/license/activate', methods=['POST'])
def activate_license():
    """Activate a license key."""
    data = request.get_json()
    license_key = data.get('license_key', '')
    payment_proof = data.get('payment_proof', '')
    
    if not license_key or not payment_proof:
        return jsonify({"error": "license_key and payment_proof are required"}), 400
    
    # Verify and activate
    success = current_app.license_manager.activate(license_key, payment_proof)
    
    if success:
        current_app.config['LICENSE_STATUS'] = 'active'
        current_app.config['LICENSE_INFO'] = {
            "status": "active",
            "license_key": license_key,
            "price": 799,
            "currency": "USD",
            "type": "lifetime",
            "activated_at": datetime.utcnow().isoformat(),
        }
        return jsonify({
            "success": True,
            "license_key": license_key,
            "message": "QFit.space activated! Welcome to the AI SaaS revolution."
        })
    else:
        return jsonify({"success": False, "error": "Invalid license key or payment proof"}), 400


@api.route('/models', methods=['GET'])
def list_models():
    """List available LLM models."""
    return jsonify(current_app.config.get('AVAILABLE_MODELS', [
        {"name": "llama3", "size": "8B", "status": "available"},
        {"name": "llama3.1", "size": "70B", "status": "available"},
        {"name": "mistral", "size": "7B", "status": "available"},
        {"name": "phi3", "size": "3.8B", "status": "available"},
    ]))


@api.route('/models/<model_name>', methods=['POST'])
def switch_model(model_name):
    """Switch to a different LLM model."""
    available = [m["name"] for m in current_app.config.get('AVAILABLE_MODELS', [])]
    if model_name in available:
        current_app.config['LLM_MODEL'] = model_name
        current_app.llm_engine.set_model(model_name)
        return jsonify({"success": True, "model": model_name})
    return jsonify({"error": f"Model {model_name} not available"}), 400


@api.route('/stats', methods=['GET'])
def get_stats():
    """Get usage statistics."""
    return jsonify({
        "total_conversations": len(current_app.conversations),
        "active_users": len(set(
            uid for conv in current_app.conversations.values() 
            if conv
        )),
        "license_status": current_app.config.get('LICENSE_STATUS', 'inactive'),
        "model": current_app.config.get('LLM_MODEL', 'llama3'),
    })


def build_prompt(message: str, history: list) -> str:
    """Build a prompt with conversation context."""
    system = (
        "You are QFit, an AI assistant for the QFit.space SaaS platform. "
        "You help users with their questions about the platform, AI features, "
        "and general assistance. Be helpful, concise, and professional."
    )
    
    context_parts = [system]
    for turn in history[-10:]:
        role = "User" if turn.get("role") == "user" else "QFit"
        context_parts.append(f"{role}: {turn.get('content', '')}")
    
    context_parts.append(f"User: {message}")
    context_parts.append("QFit:")
    
    return "\n".join(context_parts)
