from __future__ import annotations


class TestSchemaValidationError(ValueError):
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery

    def __init__(self, message: str, *, path: str = "schema") -> None:
        super().__init__(message)
        self.path = path


class TestAnswerValidationError(ValueError):
    __test__ = False  # not a pytest test class -- name collides with pytest's `Test*` discovery

    def __init__(self, message: str, *, question_key: str | None = None) -> None:
        super().__init__(message)
        self.question_key = question_key


class ResultScaleError(ValueError):
    def __init__(self, message: str, *, result_scale_key: str | None = None) -> None:
        super().__init__(message)
        self.result_scale_key = result_scale_key
