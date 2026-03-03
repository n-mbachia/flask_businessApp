# app/api/docs.py
from flasgger import Swagger

swagger_template = {
  "swagger": "2.0",
  "info": {
    "title": "Product Analytics API",
    "description": "Comprehensive product performance tracking and forecasting",
    "contact": {
      "email": "support@analytics.com"
    },
    "version": "1.0.0"
  },
  "securityDefinitions": {
    "Bearer": {
      "type": "apiKey",
      "name": "Authorization",
      "in": "header"
    }
  }
}

swagger = Swagger(template=swagger_template)

# In __init__.py add:
from app.api.docs import swagger
swagger.init_app(app)