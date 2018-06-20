
from flask import json
from flask import make_response, jsonify, Response


def response_ok(additional_data):
    json_str = json.dumps(additional_data, ensure_ascii=False).encode('utf-8').decode('utf-8')

    response = make_response(json_str, 200)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'

    return response


def response_xml(xml_str):
    return Response(response=xml_str,
                    status=200,
                    mimetype="application/xml")


def response_err(err, data=None, http_status_code=406):
    return make_response(jsonify({
        'code': err.code,
        'message': err.msg,
        'data': data
    }), http_status_code)
