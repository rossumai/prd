from anyio import Path
import asyncio

from rossum_api import ElisAPIClient
from rich import print
from rich.progress import Progress
from rich.panel import Panel

from project_rossum_deploy.commands.migrate.helpers import find_mapping_of_object
from project_rossum_deploy.common.upload import upload_schema
from project_rossum_deploy.utils.functions import (
    detemplatize_name_id,
    find_schema_id,
    read_formula_file,
    read_json,
    templatize_name_id,
)
from project_rossum_deploy.utils.consts import settings


async def migrate_schemas(
    source_path: Path,
    client: ElisAPIClient,
    mapping: dict,
    source_id_target_pairs: dict,
    sources_by_source_id_map: dict,
    progress: Progress,
):
    schema_paths = [
        schema_path async for schema_path in (source_path / "schemas").iterdir()
    ]
    task = progress.add_task("Releasing schemas...", total=len(schema_paths))

    async def migrate_schema(schema_path: Path):
        try:
            _, id = detemplatize_name_id(schema_path.stem)
            schema = await read_json(schema_path)
            sources_by_source_id_map[id] = schema

            schema["queues"] = []

            schema_mapping = find_mapping_of_object(
                mapping["organization"]["schemas"], id
            )
            if schema_mapping.get("ignore", None):
                progress.update(task, advance=1)
                return

            await update_formula_fields_code(schema_path, schema)

            result = await upload_schema(
                client, schema, schema_mapping["target_object"]
            )
            schema_mapping["target_object"] = result["id"]
            source_id_target_pairs[id] = result

            progress.update(task, advance=1)
        except Exception as e:
            print(Panel(f"Error while migrating schema: {e}"))

    await asyncio.gather(
        *[
            migrate_schema(schema_path=schema_path)
            for schema_path in schema_paths
            if await schema_path.is_file()
        ]
    )


async def update_formula_fields_code(schema_path: Path, schema: dict):
    """Checks if there is not newer code in the associated formula fields and uses that for release.
    The original schema file is not modified.
    """
    formula_directory = (
        schema_path.parent
        / f"{settings.FORMULA_DIR_PREFIX}{templatize_name_id(schema['name'], schema['id'])}"
    )
    if not await formula_directory.exists():
        return

    async for field_file_path in formula_directory.iterdir():
        formula_code = await read_formula_file(field_file_path)
        formula_name = field_file_path.stem

        schema_id = find_schema_id(schema["content"], formula_name)
        schema_id["formula"] = formula_code
