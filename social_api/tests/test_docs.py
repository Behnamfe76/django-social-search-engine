import yaml
from rest_framework import status
from rest_framework.test import APITestCase


class OpenApiSchemaTests(APITestCase):
    """The docs live under /api/, so they must be exempt from JWTRouteAuthMiddleware."""

    def test_schema_is_served_without_a_token(self):
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("openapi", response["Content-Type"])

    def test_swagger_ui_is_served_without_a_token(self):
        response = self.client.get("/api/docs/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response["Content-Type"])

    def test_redoc_is_served_without_a_token(self):
        response = self.client.get("/api/redoc/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response["Content-Type"])

    def test_ui_assets_are_local_not_cdn(self):
        content = self.client.get("/api/docs/").content.decode()

        self.assertIn("/static/drf_spectacular_sidecar/", content)
        self.assertNotIn("swagger-ui-dist@latest", content)

    def _schema(self):
        return yaml.safe_load(self.client.get("/api/schema/").content)

    def test_schema_documents_the_expected_operations(self):
        paths = self._schema()["paths"]

        for path in (
            "/api/v1/health/",
            "/api/v1/auth/register/",
            "/api/v1/auth/login/",
            "/api/v1/auth/refresh/",
            "/api/v1/auth/verify/",
            "/api/v1/auth/me/",
            "/api/v1/personalities/",
            "/api/v1/personalities/{id}/",
            "/api/v1/dashboard/",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)

    def test_schema_declares_the_jwt_security_scheme(self):
        schemes = self._schema()["components"]["securitySchemes"]

        self.assertIn("jwtAuth", schemes)
        self.assertEqual(schemes["jwtAuth"]["scheme"], "bearer")
        self.assertEqual(schemes["jwtAuth"]["bearerFormat"], "JWT")

    def test_public_endpoints_declare_no_security(self):
        paths = self._schema()["paths"]

        self.assertIsNone(paths["/api/v1/auth/login/"]["post"].get("security"))
        self.assertIsNone(paths["/api/v1/health/"]["get"].get("security"))

    def test_protected_endpoints_require_a_token(self):
        paths = self._schema()["paths"]

        security = paths["/api/v1/personalities/"]["get"]["security"]
        self.assertIn({"jwtAuth": []}, security)
        self.assertIn({"jwtAuth": []}, paths["/api/v1/auth/me/"]["get"]["security"])
        self.assertIn({"jwtAuth": []}, paths["/api/v1/dashboard/"]["get"]["security"])

    def test_dashboard_takes_no_query_parameters(self):
        """It is a fixed snapshot; a documented filter would be a lie."""
        operation = self._schema()["paths"]["/api/v1/dashboard/"]["get"]

        self.assertEqual(operation.get("parameters", []), [])
