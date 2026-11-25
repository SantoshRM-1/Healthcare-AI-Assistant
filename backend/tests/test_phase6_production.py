import unittest

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request

from app.core.auth import get_principal
from app.core.errors import database_error_response


class ProductionSafetyTests(unittest.TestCase):
    def test_missing_bearer_token_is_rejected_without_external_calls(self):
        with self.assertRaises(HTTPException) as raised:
            get_principal(None).send(None)
        self.assertEqual(raised.exception.status_code, 401)

    def test_database_errors_are_logged_but_not_returned_to_clients(self):
        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/failure",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
            "http_version": "1.1",
        })
        error = SQLAlchemyError("postgres-password=secret; table patient_reports missing")
        response = database_error_response(request, error)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.body.decode())
        self.assertNotIn("patient_reports", response.body.decode())


if __name__ == "__main__":
    unittest.main()
