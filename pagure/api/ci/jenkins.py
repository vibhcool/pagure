# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

from cryptography.hazmat.primitives import constant_time
from kitchen.text.converters import to_bytes

import pagure
import pagure.exceptions
import pagure.lib
import pagure.lib.lib_ci as lib_ci
from pagure import APP, SESSION
from pagure.api import API, APIERROR, api_method


@API.route('/ci/jenkins/<repo>/<pagure_ci_token>/build-finished',
           methods=['POST'])
@API.route('/ci/jenkins/<namespace>/<repo>/<pagure_ci_token>/build-finished',
           methods=['POST'])
@API.route('/ci/jenkins/forks/<username>/<repo>/'
           '<pagure_ci_token>/build-finished', methods=['POST'])
@API.route('/ci/jenkins/forks/<username>/<namespace>/<repo>/'
           '<pagure_ci_token>/build-finished', methods=['POST'])
@api_method
def jenkins_ci_notification(
        repo, pagure_ci_token, username=None, namespace=None):
    """
    Jenkins Build Notification
    --------------------------
    At the end of a build on Jenkins, this URL is used (if the project is
    rightly configured) to flag a pull-request with the result of the build.

    ::

        POST /api/0/ci/jenkins/<repo>/<token>/build-finished

    """

    project = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)
    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not constant_time.bytes_eq(
            to_bytes(pagure_ci_token),
            to_bytes(project.ci_hook.pagure_ci_token)):
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    data = flask.request.get_json()
    if not data:
        APP.logger.debug("Bad Request: No JSON retrieved")
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    build_id = data.get('build', {}).get('number')
    if not build_id:
        APP.logger.debug("Bad Request: No build ID retrieved")
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    try:
        lib_ci.process_jenkins_build(
            SESSION,
            project,
            build_id,
            requestfolder=APP.config['REQUESTS_FOLDER']
        )
    except pagure.exceptions.NoCorrespondingPR as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err))
    except pagure.exceptions.PagureException as err:
        APP.logger.error('Error processing jenkins notification', exc_info=err)
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err))

    APP.logger.info('Successfully proccessed jenkins notification')
    return ('', 204)
