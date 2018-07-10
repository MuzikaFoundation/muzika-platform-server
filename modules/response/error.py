from flask import request
from modules.lang import get_best_fit_language

"""
 Defines error codes and error messages for the server response.
"""


class ErrorResponse:
    def __init__(self, code, **messages):
        self.code = code
        self.error_msg = messages

    @property
    def msg(self):
        """
        Gets message with best fit language.
        :return: a message with best fit language.
        """
        try:
            return self.error_msg[request.lang]
        except AttributeError:
            # if request.lang does not exist
            return self.error_msg[get_best_fit_language()]


class _ErrCommon:
    INVALID_REQUEST_BODY = ErrorResponse(
        code=1,
        en='Invalid request body.',
        ko='잘못된 요청입니다.',
    )

    INVALID_SIGNATURE = ErrorResponse(
        code=2,
        en='Invalid signature.',
        ko='잘못된 서명입니다.',
    )

    NOT_EXIST = ErrorResponse(
        code=3,
        en='Object does not exist.',
        ko='존재하지 않습니다.',
    )

    AUTHENTICATION_FAILED = ErrorResponse(
        code=4,
        en='Failed to authenticate.',
        ko='인증에 실패하였습니다.',
    )

    ALREADY_EXIST = ErrorResponse(
        code=5,
        en='Already exists.',
        ko='이미 존재합니다.',
    )

    UPLOAD_FAIL = ErrorResponse(
        code=6,
        en='Failed to upload.',
        ko='업로드에 실패하였습니다.',
    )

    TX_HASH_DUPLICATED = ErrorResponse(
        code=7,
        en='Transaction already exists.',
        ko='트랜젝션이 이미 존재합니다.',
    )

    INVALID_TX_HASH = ErrorResponse(
        code=8,
        en='Invalid transaction.',
        ko='유효하지 않은 트랜젝션입니다.',
    )

    TOO_LONG_PARAMETER = ErrorResponse(
        code=9,
        en='Too long parameter.',
        ko='인자 값이 너무 깁니다.',
    )

    TOO_SHORT_PARAMETER = ErrorResponse(
        code=10,
        en='Too short parameter.',
        ko='인자 값이 너무 짧습니다.',
    )

    FILE_SIZE_LIMIT_EXCEEDED = ErrorResponse(
        code=11,
        en='File size is too big.',
        ko='파일 크기가 너무 큽니다.',
    )

    NOT_ALLOWED_CONTENT_TYPE = ErrorResponse(
        code=12,
        en='Not allowed content type.',
        ko='컨텐츠 타입이 올바르지 않습니다.',
    )

    TOO_MANY_REQUEST = ErrorResponse(
        code=13,
        en='Server blocks your requests temporarily because of too many requests',
        ko='잦은 요청으로 인하여 일시적으로 차단되었습니다.'
    )


class _ErrDraft:
    NOT_EXISTS = ErrorResponse(
        code=101,
        en='Draft not exists',
        ko='초본이 존재하지 않습니다.'
    )

    ALREADY_UPLOADED = ErrorResponse(
        code=101,
        en='It already uploaded to new posts',
        ko='이미 업로드 된 게시글입니다.'
    )


class ERR:
    COMMON = _ErrCommon
    DRAFT = _ErrDraft
