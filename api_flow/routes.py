from flask import Blueprint, request, jsonify

from lia_bot import LIAQueryBot

api_bp = Blueprint('api_flow', __name__)


@api_bp.route('/api/verify-agent-license', methods=['POST'])
def verify_agent_license():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"status_code": 2, "message": "Failed: Invalid ID alphanumeric format."}), 400

    license_number = data.get('license_number')
    if not license_number:
        return jsonify({"status_code": 2, "message": "Failed: Invalid ID alphanumeric format."})

    if not license_number.isdigit() or len(license_number) < 8 or len(license_number) > 10:
        return jsonify({"status_code": 2, "message": "Failed: Invalid ID alphanumeric format."})

    reg_no = license_number.zfill(10)

    bot = None
    try:
        bot = LIAQueryBot(headless=True)
        bot.start()
        result = bot.perform_query(reg_no, skip_screenshot=True)

        status = result.get('status')
        if status == 'found_valid':
            return jsonify({"status_code": 0, "message": "Verification passed: New agent identified."})
        elif status == 'found_invalid':
            return jsonify({"status_code": 1, "message": "Failed: Not a new agent (seniority > 1 year)."})
        elif status == 'not_found':
            return jsonify({"status_code": 3, "message": "Failed: License number not found in database."})
        else:
            return jsonify({"status_code": 999, "message": "Error: Third-party service is under maintenance."})
    except Exception:
        return jsonify({"status_code": 999, "message": "Error: Third-party service is under maintenance."})
    finally:
        if bot:
            bot.close()
