"""
API documentation generator and utilities.
"""
from flask import Blueprint, jsonify, render_template
from typing import Dict, List, Any
import inspect
from .api_utils import APIDocumentation, APIResponse


class APIDocGenerator:
    """Generates comprehensive API documentation."""
    
    def __init__(self):
        self.endpoints = {}
        self.categories = {
            'Authentication': [],
            'Products': [],
            'Orders': [],
            'Analytics': [],
            'Users': []
        }
    
    def register_endpoint(self, blueprint_name: str, endpoint_name: str,
                      methods: List[str], description: str,
                      parameters: List[Dict[str, Any]] = None,
                      responses: Dict[str, Dict[str, str]] = None,
                      category: str = 'General'):
        """
        Register an endpoint for documentation.
        
        Args:
            blueprint_name: Name of the Flask blueprint
            endpoint_name: Name of the endpoint
            methods: HTTP methods supported
            description: Endpoint description
            parameters: List of parameter documentation
            responses: Dictionary of response documentation
            category: Category for grouping endpoints
        """
        endpoint_doc = APIDocumentation.generate_endpoint_docs(
            endpoint_name=endpoint_name,
            methods=methods,
            description=description,
            parameters=parameters,
            responses=responses
        )
        
        self.endpoints[f"{blueprint_name}.{endpoint_name}"] = endpoint_doc
        
        if category not in self.categories:
            self.categories[category] = []
        
        self.categories[category].append({
            'blueprint': blueprint_name,
            'endpoint': endpoint_name,
            'doc': endpoint_doc
        })
    
    def generate_full_documentation(self) -> Dict[str, Any]:
        """
        Generate complete API documentation.
        
        Returns:
            Complete API documentation dictionary
        """
        return {
            'api_info': {
                'title': 'Business Application API',
                'version': 'v1',
                'description': 'RESTful API for business application management',
                'base_url': '/api/v1',
                'contact': {
                    'email': 'support@example.com',
                    'name': 'API Support'
                },
                'license': {
                    'name': 'MIT',
                    'url': 'https://opensource.org/licenses/MIT'
                }
            },
            'categories': self.categories,
            'endpoints': self.endpoints,
            'common_responses': {
                '200': {
                    'description': 'Success',
                    'schema': {'type': 'object', 'properties': {
                        'status': {'type': 'string', 'example': 'success'},
                        'message': {'type': 'string', 'example': 'Operation completed'},
                        'data': {'type': 'object'},
                        'timestamp': {'type': 'string', 'format': 'date-time'}
                    }}
                },
                '201': {
                    'description': 'Created',
                    'schema': {'type': 'object', 'properties': {
                        'status': {'type': 'string', 'example': 'success'},
                        'message': {'type': 'string', 'example': 'Resource created'},
                        'data': {'type': 'object'},
                        'timestamp': {'type': 'string', 'format': 'date-time'}
                    }}
                },
                '400': {
                    'description': 'Bad Request',
                    'schema': {'type': 'object', 'properties': {
                        'status': {'type': 'string', 'example': 'error'},
                        'message': {'type': 'string', 'example': 'Invalid request'},
                        'error_code': {'type': 'string'},
                        'details': {'type': 'object'},
                        'timestamp': {'type': 'string', 'format': 'date-time'}
                    }}
                },
                '401': {
                    'description': 'Unauthorized',
                    'schema': {'type': 'object', 'properties': {
                        'status': {'type': 'string', 'example': 'error'},
                        'message': {'type': 'string', 'example': 'Authentication required'},
                        'timestamp': {'type': 'string', 'format': 'date-time'}
                    }}
                },
                '403': {
                    'description': 'Forbidden',
                    'schema': {'type': 'object', 'properties': {
                        'status': {'type': 'string', 'example': 'error'},
                        'message': {'type': 'string', 'example': 'Access denied'},
                        'timestamp': {'type': 'string', 'format': 'date-time'}
                    }}
                },
                '404': {
                    'description': 'Not Found',
                    'schema': {'type': 'object', 'properties': {
                        'status': {'type': 'string', 'example': 'error'},
                        'message': {'type': 'string', 'example': 'Resource not found'},
                        'timestamp': {'type': 'string', 'format': 'date-time'}
                    }}
                },
                '422': {
                    'description': 'Validation Error',
                    'schema': {'type': 'object', 'properties': {
                        'status': {'type': 'string', 'example': 'error'},
                        'message': {'type': 'string', 'example': 'Validation failed'},
                        'error_code': {'type': 'string', 'example': 'VALIDATION_ERROR'},
                        'details': {'type': 'object', 'properties': {
                            'validation_errors': {'type': 'object'}
                        }},
                        'timestamp': {'type': 'string', 'format': 'date-time'}
                    }}
                },
                '429': {
                    'description': 'Rate Limit Exceeded',
                    'schema': {'type': 'object', 'properties': {
                        'status': {'type': 'string', 'example': 'error'},
                        'message': {'type': 'string', 'example': 'Rate limit exceeded'},
                        'error_code': {'type': 'string', 'example': 'RATE_LIMIT_EXCEEDED'},
                        'details': {'type': 'object', 'properties': {
                            'limit': {'type': 'integer'},
                            'reset_time': {'type': 'integer'},
                            'retry_after': {'type': 'integer'}
                        }},
                        'timestamp': {'type': 'string', 'format': 'date-time'}
                    }}
                },
                '500': {
                    'description': 'Internal Server Error',
                    'schema': {'type': 'object', 'properties': {
                        'status': {'type': 'string', 'example': 'error'},
                        'message': {'type': 'string', 'example': 'Internal server error'},
                        'error_code': {'type': 'string', 'example': 'INTERNAL_ERROR'},
                        'timestamp': {'type': 'string', 'format': 'date-time'}
                    }}
                }
            },
            'authentication': {
                'description': 'API uses JWT tokens for authentication',
                'type': 'Bearer',
                'header': 'Authorization: Bearer <token>',
                'endpoints': [
                    '/auth/login',
                    '/auth/register'
                ]
            },
            'rate_limiting': {
                'description': 'API implements rate limiting',
                'headers': {
                    'X-RateLimit-Limit': 'Request limit per window',
                    'X-RateLimit-Remaining': 'Remaining requests in current window',
                    'X-RateLimit-Reset': 'Unix timestamp when limit resets'
                },
                'limits': {
                    'default': '1000 requests per hour',
                    'auth': '5 requests per minute',
                    'search': '30 requests per minute'
                }
            }
        }
    
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """
        Generate OpenAPI 3.0 specification.
        
        Returns:
            OpenAPI specification dictionary
        """
        return {
            'openapi': '3.0.0',
            'info': {
                'title': 'Business Application API',
                'description': 'RESTful API for business application management',
                'version': '1.0.0',
                'contact': {
                    'email': 'support@example.com',
                    'name': 'API Support'
                },
                'license': {
                    'name': 'MIT',
                    'url': 'https://opensource.org/licenses/MIT'
                }
            },
            'servers': [
                {
                    'url': 'https://api.example.com/v1',
                    'description': 'Production server'
                },
                {
                    'url': 'https://staging-api.example.com/v1',
                    'description': 'Staging server'
                }
            ],
            'paths': self._generate_openapi_paths(),
            'components': {
                'schemas': self._generate_openapi_schemas(),
                'securitySchemes': {
                    'bearerAuth': {
                        'type': 'http',
                        'scheme': 'bearer',
                        'bearerFormat': 'JWT'
                    }
                }
            },
            'security': [
                {
                    'bearerAuth': []
                }
            ]
        }
    
    def _generate_openapi_paths(self) -> Dict[str, Any]:
        """Generate OpenAPI paths from registered endpoints."""
        paths = {}
        
        for endpoint_key, endpoint_doc in self.endpoints.items():
            path_item = {}
            
            for method in endpoint_doc['methods']:
                method_lower = method.lower()
                path_item[method_lower] = {
                    'summary': endpoint_doc['description'],
                    'description': endpoint_doc['description'],
                    'parameters': endpoint_doc.get('parameters', []),
                    'responses': endpoint_doc.get('responses', {}),
                    'tags': [self._get_endpoint_category(endpoint_key)]
                }
            
            # Extract path from endpoint key
            path = self._extract_path_from_endpoint(endpoint_key)
            paths[path] = path_item
        
        return paths
    
    def _generate_openapi_schemas(self) -> Dict[str, Any]:
        """Generate OpenAPI schemas."""
        return {
            'SuccessResponse': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'example': 'success'
                    },
                    'message': {
                        'type': 'string',
                        'example': 'Operation completed successfully'
                    },
                    'data': {
                        'type': 'object'
                    },
                    'timestamp': {
                        'type': 'string',
                        'format': 'date-time'
                    }
                }
            },
            'ErrorResponse': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'example': 'error'
                    },
                    'message': {
                        'type': 'string',
                        'example': 'An error occurred'
                    },
                    'error_code': {
                        'type': 'string',
                        'example': 'VALIDATION_ERROR'
                    },
                    'timestamp': {
                        'type': 'string',
                        'format': 'date-time'
                    }
                }
            },
            'ValidationError': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'example': 'error'
                    },
                    'message': {
                        'type': 'string',
                        'example': 'Validation failed'
                    },
                    'error_code': {
                        'type': 'string',
                        'example': 'VALIDATION_ERROR'
                    },
                    'details': {
                        'type': 'object',
                        'properties': {
                            'validation_errors': {
                                'type': 'object',
                                'additionalProperties': True
                            }
                        }
                    },
                    'timestamp': {
                        'type': 'string',
                        'format': 'date-time'
                    }
                }
            },
            'PaginatedResponse': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'example': 'success'
                    },
                    'message': {
                        'type': 'string',
                        'example': 'Data retrieved successfully'
                    },
                    'data': {
                        'type': 'array',
                        'items': {
                            'type': 'object'
                        }
                    },
                    'meta': {
                        'type': 'object',
                        'properties': {
                            'pagination': {
                                '$ref': '#/components/schemas/Pagination'
                            }
                        }
                    }
                }
            },
            'Pagination': {
                'type': 'object',
                'properties': {
                    'current_page': {
                        'type': 'integer',
                        'example': 1
                    },
                    'per_page': {
                        'type': 'integer',
                        'example': 20
                    },
                    'total_items': {
                        'type': 'integer',
                        'example': 100
                    },
                    'total_pages': {
                        'type': 'integer',
                        'example': 5
                    },
                    'has_next': {
                        'type': 'boolean',
                        'example': True
                    },
                    'has_prev': {
                        'type': 'boolean',
                        'example': False
                    }
                }
            }
        }
    
    def _get_endpoint_category(self, endpoint_key: str) -> str:
        """Get category for an endpoint."""
        for category, endpoints in self.categories.items():
            for endpoint in endpoints:
                if f"{endpoint['blueprint']}.{endpoint['endpoint']}" == endpoint_key:
                    return category
        return 'General'
    
    def _extract_path_from_endpoint(self, endpoint_key: str) -> str:
        """Extract URL path from endpoint key."""
        # This is a simplified version - in practice, you'd parse Flask routes
        blueprint_name, endpoint_name = endpoint_key.split('.', 1)
        
        # Map common endpoints to paths
        path_mapping = {
            'auth.login': '/auth/login',
            'auth.register': '/auth/register',
            'products.manage_products': '/products',
            'products.search': '/products/search',
            'products.delete': '/products/{id}',
            'analytics.sales': '/analytics/sales',
            'analytics.revenue': '/analytics/revenue'
        }
        
        return path_mapping.get(endpoint_key, f'/{endpoint_name}')


# Global documentation generator instance
doc_generator = APIDocGenerator()


def api_documented(blueprint_name: str, endpoint_name: str,
                  methods: List[str], description: str,
                  parameters: List[Dict[str, Any]] = None,
                  responses: Dict[str, Dict[str, str]] = None,
                  category: str = 'General'):
    """
    Decorator to automatically document API endpoints.
    
    Args:
        blueprint_name: Name of the Flask blueprint
        endpoint_name: Name of the endpoint
        methods: HTTP methods supported
        description: Endpoint description
        parameters: List of parameter documentation
        responses: Dictionary of response documentation
        category: Category for grouping endpoints
        
    Returns:
        Decorator function
    """
    def decorator(func):
        # Register endpoint for documentation
        doc_generator.register_endpoint(
            blueprint_name=blueprint_name,
            endpoint_name=endpoint_name,
            methods=methods,
            description=description,
            parameters=parameters,
            responses=responses,
            category=category
        )
        
        return func
    return decorator


# Blueprint for API documentation
api_docs_bp = Blueprint('api_docs', __name__)


@api_docs_bp.route('/docs')
def api_documentation():
    """Serve API documentation page."""
    try:
        docs = doc_generator.generate_full_documentation()
        return render_template('api/docs.html', docs=docs)
    except Exception as e:
        return APIResponse.error(
            message="Failed to generate documentation",
            status_code=500
        )


@api_docs_bp.route('/docs/json')
def api_documentation_json():
    """Serve API documentation as JSON."""
    try:
        docs = doc_generator.generate_full_documentation()
        return APIResponse.success(data=docs, message="API documentation retrieved")
    except Exception as e:
        return APIResponse.error(
            message="Failed to generate documentation",
            status_code=500
        )


@api_docs_bp.route('/docs/openapi.json')
def openapi_specification():
    """Serve OpenAPI specification."""
    try:
        spec = doc_generator.generate_openapi_spec()
        response = jsonify(spec)
        response.headers['Content-Type'] = 'application/vnd.oai.openapi+json;version=3.0.0'
        return response
    except Exception as e:
        return APIResponse.error(
            message="Failed to generate OpenAPI spec",
            status_code=500
        )


@api_docs_bp.route('/docs/postman')
def postman_collection():
    """Generate Postman collection for API testing."""
    try:
        collection = {
            'info': {
                'name': 'Business Application API',
                'description': 'Postman collection for Business Application API',
                'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
            },
            'item': []
        }
        
        # Add endpoints to collection
        for category, endpoints in doc_generator.categories.items():
            for endpoint in endpoints:
                if 'POST' in endpoint['doc']['methods']:
                    collection['item'].append({
                        'name': endpoint['doc']['endpoint'],
                        'request': {
                            'method': 'POST',
                            'header': [
                                {
                                    'key': 'Content-Type',
                                    'value': 'application/json'
                                },
                                {
                                    'key': 'Authorization',
                                    'value': 'Bearer {{token}}'
                                }
                            ],
                            'body': {
                                'mode': 'raw',
                                'raw': '{\n  "field1": "value1",\n  "field2": "value2"\n}'
                            },
                            'url': {
                                'raw': '{{base_url}}' + endpoint['doc'].get('path', f'/{endpoint["endpoint"]}'),
                                'host': ['{{base_url}}']
                            }
                        }
                    })
        
        return jsonify(collection)
    except Exception as e:
        return APIResponse.error(
            message="Failed to generate Postman collection",
            status_code=500
        )
