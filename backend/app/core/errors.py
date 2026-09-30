from fastapi import HTTPException, status


class ApiError(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = 400, **extra):
        detail = {"code": code, "message": message, **extra}
        super().__init__(status_code=status_code, detail=detail)


def unauthorized(message: str = "Не авторизован", code: str = "unauthorized") -> ApiError:
    return ApiError(code, message, status_code=status.HTTP_401_UNAUTHORIZED)


def forbidden(message: str = "Доступ запрещён", code: str = "forbidden") -> ApiError:
    return ApiError(code, message, status_code=status.HTTP_403_FORBIDDEN)


def consent_required(
    message: str = "Требуется согласие на обработку персональных данных",
    code: str = "consent_required",
    **extra,
) -> ApiError:
    """Task 064 -- distinguishable from a plain `forbidden` so the mini-app can render the
    consent gate instead of a generic access-denied state. `extra` carries `policy_url`/
    `policy_version` so the gate screen doesn't need a second round-trip."""
    return ApiError(code, message, status_code=status.HTTP_403_FORBIDDEN, **extra)


def not_found(message: str = "Не найдено", code: str = "not_found", **extra) -> ApiError:
    return ApiError(code, message, status_code=status.HTTP_404_NOT_FOUND, **extra)


def bad_request(message: str, code: str = "bad_request", **extra) -> ApiError:
    return ApiError(code, message, status_code=status.HTTP_400_BAD_REQUEST, **extra)


def unprocessable(message: str, code: str = "unprocessable_entity", **extra) -> ApiError:
    return ApiError(code, message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, **extra)


def conflict(message: str, code: str = "conflict", **extra) -> ApiError:
    return ApiError(code, message, status_code=status.HTTP_409_CONFLICT, **extra)


def service_unavailable(message: str, code: str = "service_unavailable", **extra) -> ApiError:
    return ApiError(code, message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, **extra)
