import json

from anyio import Path
from rossum_api import ElisAPIClient
from rossum_api.api_client import Resource

from project_rossum_deploy.commands.upload.helpers import (
    determine_object_type_from_path,
    determine_object_type_from_url,
)
from project_rossum_deploy.utils.consts import GIT_CHARACTERS
from project_rossum_deploy.utils.functions import (
    detemplatize_name_id,
    display_error,
    read_json,
    write_json,
)


async def update_object(
    client: ElisAPIClient, path: Path = None, object: dict = None, errors: list = []
):
    try:
        if not object:
            object = await read_json(path)

        id, url = object.get("id", None), object.get("url", None)
        if not id:
            raise Exception("Missing object ID")
        if not url:
            raise Exception("Missing object URL")

        resource = determine_object_type_from_url(url)
        # Inboxes are ready-only in Elis API, but we don't ignore them when pulling to distinguish queues with and without inboxes
        if resource == Resource.Queue:
            object.pop("inbox", None)

        result = await client._http_client.update(resource, id, object)

        print(f'Successfully updated {resource} with ID "{id}".')
        return result
    except Exception as e:
        if path:
            display_error(f'Error while updating object with path "{path}": {e}', e)
        else:
            id = object.get("id", None)
            descriptor = id if id else json.dump(object)
            display_error(f"Error while updating object {descriptor}: {e}", e)
        errors.append({"op": GIT_CHARACTERS.UPDATED, "path": path})


async def create_object(path: Path, client: ElisAPIClient, errors: list):
    try:
        object = await read_json(path)
        object["id"] = None
        resource = determine_object_type_from_path(path)
        created_object = await client._http_client.create(resource, object)
        await write_json(path, created_object)
        print(f'Successfully create {resource} with ID "{created_object["id"]}".')
    except Exception as e:
        display_error(f'Error while creating object with path "{path}": {e}', e)
        errors.append({"op": GIT_CHARACTERS.CREATED, "path": path})


async def delete_object(path: Path, client: ElisAPIClient, errors: list):
    try:
        _, id = detemplatize_name_id(path)
        resource = determine_object_type_from_path(path)
        await client._http_client.delete(resource, id)
        print(f'Successfully deleted {resource} with ID "{id}".')
    except Exception as e:
        display_error(f'Error while deleting object with path "{path}": {e}', e)
        errors.append({"op": GIT_CHARACTERS.DELETED, "path": path})
