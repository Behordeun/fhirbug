from fhirball.server.requestparser import parse_url
from fhirball.exceptions import MappingValidationError, QueryValidationError, ConfigurationError

from fhirball.Fhir.resources import OperationOutcome, FHIRValidationError
from fhirball.config import import_models, settings


def handle_get_request(url):
  """
  Receive a request url as a string and handle it. This includes parsing the string into a
  :class:`fhirball.server.requestparser.FhirRequestQuery`, finding the model for the requested
  resource and calling `Resource.get` on it.
  It returns a tuple (response json, status code).
  If an error occurs during the process, an OperationOutcome is returned.

  :param url: a string containing the path of the request. It should not contain the server
              path. For example: `Patients/123?name:contains=Jo`
  :returns: (response json, status code) Where response_json may be the requested resource,
            a Bundle or an OperationOutcome in case of an error.

  """
  # Try to parse the url
  try:
    query = parse_url(url)
  except QueryValidationError as e:
    op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'bad-request', 'diagnostics': f'{e}'}]})
    return op.as_json(), 400

  resource = query.resource
  try:
      models = import_models()
  except ConfigurationError:
      op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'server-error', 'diagnostics': f'The server is improprly configured'}]})
      return op.as_json(), 500

  # Try to import the resource map class
  try:
    Resource = getattr(models, resource)
  except Exception as e:
    op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'not-found', 'diagnostics': f'Resource type \"{resource}\" does not exist or is not supported.'}]})
    return op.as_json(), 404

  # Try to fetch the requested resource(s)
  try:
    res = Resource.get(query=query)
    return res, 200
  except (MappingValidationError, FHIRValidationError) as e:
    op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'not-found', 'diagnostics': f'{e}'}]})
    return op.as_json(), 404
  except Exception as e:
    op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'server-error', 'diagnostics': f'{e}'}]})
    import traceback
    print(traceback.format_exc())
    return op.as_json(), 500


def handle_post_request(url, body):
    """
    Receive a request url and the request body of a POST request and handle it. This includes parsing the string into a
    :class:`fhirball.server.requestparser.FhirRequestQuery`, finding the model for the requested
    resource and creating a new instance.
    It returns a tuple (response json, status code).
    If an error occurs during the process, an OperationOutcome is returned.

    :param url: a string containing the path of the request. It should not contain the server
                path. For example: `Patients/123?name:contains=Jo`
    :type url: string
    :param body: a dictionary containing all data that was sent with the request
    :type body: dict

    :returns: A tuple ``(response_json, status code)``, where response_json may be the requested resource,
              a Bundle or an OperationOutcome in case of an error.
    :rtype: tuple

    """
    query = parse_url(url)
    resource_name = query.resource

    try:
        models = import_models()
    except ConfigurationError:
        op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'server-error', 'diagnostics': f'The server is improprly configured'}]})
        return op.as_json(), 500

    # Get the Resource
    try:
        from fhirball.Fhir import resources
        Resource = getattr(resources, resource_name)
    except Exception as e:
        op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'not-found', 'diagnostics': f'Resource \"{resource_name}\" does not exist.'}]})
        return op.as_json(), 404
    # Validate the incoming json
    try:
        resource = Resource(body)
    except Exception as e:
        op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'validation', 'diagnostics': f'{e}'}]})
        return op.as_json(), 400
    # Import the model
    try:
        Model = getattr(models, resource_name)
    except Exception as e:
        return {'error': 'This shouldn\'t happen', 'exception': str(e)}, 404

    try:
        new_resource = Model.create_from_resource(resource, query=query)
    except Exception as e:
        if settings.DEBUG:
            import traceback
            print(traceback.format_exc())
            op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'validation', 'diagnostics': traceback.format_exc()}]})
        else:
            op = OperationOutcome({'issue': [{'severity': 'error', 'code': 'validation', 'diagnostics': f'{e}'}]})

        return op.as_json(), 422
    # new_resource.save()
    return new_resource.to_fhir().as_json(), 201