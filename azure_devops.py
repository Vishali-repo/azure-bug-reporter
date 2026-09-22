import base64
import os
import sys
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv


# =========================================================
# Find Application Folder
# =========================================================

if getattr(sys, "frozen", False):
    BASE_DIR = Path(
        sys.executable
    ).resolve().parent
else:
    BASE_DIR = Path(
        __file__
    ).resolve().parent


# =========================================================
# Load .env
# =========================================================

ENV_FILE = BASE_DIR / ".env"

load_dotenv(
    ENV_FILE
)


AZURE_ORG = os.getenv(
    "AZURE_ORG"
)

AZURE_PAT = os.getenv(
    "AZURE_PAT"
)

API_VERSION = "7.1"


# =========================================================
# Azure DevOps Client
# =========================================================

class AzureDevOpsClient:

    def __init__(self):

        if not AZURE_ORG:

            raise RuntimeError(
                f"AZURE_ORG is missing.\n\n"
                f"Please check the .env file:\n"
                f"{ENV_FILE}"
            )

        if not AZURE_PAT:

            raise RuntimeError(
                f"AZURE_PAT is missing.\n\n"
                f"Please check the .env file:\n"
                f"{ENV_FILE}"
            )

        self.organization = AZURE_ORG

        self.base_url = (
            f"https://dev.azure.com/"
            f"{self.organization}"
        )

        token = base64.b64encode(
            f":{AZURE_PAT}".encode(
                "utf-8"
            )
        ).decode(
            "utf-8"
        )

        self.headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json"
        }

    # =====================================================
    # GET PROJECTS
    # =====================================================

    def get_projects(self):

        url = (
            f"{self.base_url}/"
            f"_apis/projects"
            f"?api-version={API_VERSION}"
        )

        response = requests.get(
            url,
            headers=self.headers,
            timeout=30
        )

        if not response.ok:

            raise RuntimeError(
                f"Azure DevOps error "
                f"{response.status_code}: "
                f"{response.text}"
            )

        data = response.json()

        projects = []

        for project in data.get(
            "value",
            []
        ):

            if project.get(
                "state"
            ) == "wellFormed":

                projects.append(
                    {
                        "id": project["id"],
                        "name": project["name"]
                    }
                )

        projects.sort(
            key=lambda x:
            x["name"].lower()
        )

        return projects

    # =====================================================
    # SEARCH PARENT TASKS
    # =====================================================

    def search_parent_tasks(
        self,
        project_name,
        search_text
    ):

        search_text = (
            search_text.strip()
        )

        if not search_text:

            return []

        escaped_project = (
            project_name.replace(
                "'",
                "''"
            )
        )

        # -------------------------------------------------
        # Exact Task ID Search
        # -------------------------------------------------

        if search_text.isdigit():

            wiql_query = f"""
                SELECT
                    [System.Id],
                    [System.Title]
                FROM WorkItems
                WHERE
                    [System.TeamProject] = '{escaped_project}'
                    AND [System.WorkItemType] = 'Task'
                    AND [System.Id] = {search_text}
            """

        # -------------------------------------------------
        # Task Title Search
        # -------------------------------------------------

        else:

            escaped_search = (
                search_text.replace(
                    "'",
                    "''"
                )
            )

            wiql_query = f"""
                SELECT
                    [System.Id],
                    [System.Title]
                FROM WorkItems
                WHERE
                    [System.TeamProject] = '{escaped_project}'
                    AND [System.WorkItemType] = 'Task'
                    AND [System.Title] CONTAINS '{escaped_search}'
                ORDER BY [System.Id] DESC
            """

        # -------------------------------------------------
        # WIQL Request
        # -------------------------------------------------

        url = (
            f"{self.base_url}/"
            f"{quote(project_name)}/"
            f"_apis/wit/wiql"
            f"?$top=25"
            f"&api-version={API_VERSION}"
        )

        headers = self.headers.copy()

        headers["Content-Type"] = (
            "application/json"
        )

        response = requests.post(
            url,
            headers=headers,
            json={
                "query": wiql_query
            },
            timeout=15
        )

        if not response.ok:

            raise RuntimeError(
                "Parent Task search failed.\n\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text}"
            )

        data = response.json()

        work_items = data.get(
            "workItems",
            []
        )

        if not work_items:

            return []

        # -------------------------------------------------
        # Get maximum 25 IDs
        # -------------------------------------------------

        ids = [
            str(item["id"])
            for item in work_items[:25]
        ]

        if not ids:

            return []

        # -------------------------------------------------
        # Get Task Details in ONE Request
        # -------------------------------------------------

        ids_string = ",".join(
            ids
        )

        details_url = (
            f"{self.base_url}/"
            f"_apis/wit/workitems"
            f"?ids={ids_string}"
            f"&fields="
            f"System.Id,"
            f"System.Title,"
            f"System.State"
            f"&api-version={API_VERSION}"
        )

        details_response = requests.get(
            details_url,
            headers=self.headers,
            timeout=15
        )

        if not details_response.ok:

            raise RuntimeError(
                "Unable to retrieve Parent Task details.\n\n"
                f"Status: "
                f"{details_response.status_code}\n"
                f"Response: "
                f"{details_response.text}"
            )

        details_data = (
            details_response.json()
        )

        results = []

        for item in details_data.get(
            "value",
            []
        ):

            fields = item.get(
                "fields",
                {}
            )

            results.append(
                {
                    "id": item.get(
                        "id"
                    ),
                    "title": fields.get(
                        "System.Title",
                        ""
                    ),
                    "state": fields.get(
                        "System.State",
                        ""
                    )
                }
            )

        # -------------------------------------------------
        # Preserve WIQL Order
        # -------------------------------------------------

        order = {
            str(item_id): index
            for index, item_id
            in enumerate(ids)
        }

        results.sort(
            key=lambda item:
            order.get(
                str(item["id"]),
                999
            )
        )

        return results[:25]

    # =====================================================
    # UPLOAD ATTACHMENT
    # =====================================================

    def upload_attachment(
        self,
        project_name,
        file_path
    ):

        if not os.path.exists(
            file_path
        ):

            raise RuntimeError(
                f"Screenshot not found:\n"
                f"{file_path}"
            )

        file_name = os.path.basename(
            file_path
        )

        encoded_file_name = quote(
            file_name
        )

        url = (
            f"{self.base_url}/"
            f"{quote(project_name)}/"
            f"_apis/wit/attachments"
            f"?fileName={encoded_file_name}"
            f"&api-version={API_VERSION}"
        )

        headers = self.headers.copy()

        headers["Content-Type"] = (
            "application/octet-stream"
        )

        with open(
            file_path,
            "rb"
        ) as file:

            response = requests.post(
                url,
                headers=headers,
                data=file,
                timeout=60
            )

        if not response.ok:

            raise RuntimeError(
                "Attachment upload failed.\n\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text}"
            )

        data = response.json()

        attachment_url = data.get(
            "url"
        )

        if not attachment_url:

            raise RuntimeError(
                "Azure DevOps did not return "
                "an attachment URL."
            )

        return attachment_url

    # =====================================================
    # CREATE BUG
    # =====================================================

    def create_bug(
        self,
        project_name,
        bug_title,
        parent_task_id,
        bug_category,
        attachment_url
    ):

        try:

            parent_task_id = int(
                parent_task_id
            )

        except (
            ValueError,
            TypeError
        ):

            raise RuntimeError(
                "Parent Task ID must be a number."
            )

        if not bug_category:

            raise RuntimeError(
                "Bug Category is required."
            )

        url = (
            f"{self.base_url}/"
            f"{quote(project_name)}/"
            f"_apis/wit/workitems/$Bug"
            f"?api-version={API_VERSION}"
        )

        patch_document = [

            {
                "op": "add",
                "path": "/fields/System.Title",
                "value": bug_title
            },

            {
                "op": "add",
                "path": "/fields/Custom.BugCategory",
                "value": bug_category
            },

            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": (
                        "System.LinkTypes."
                        "Hierarchy-Reverse"
                    ),
                    "url": (
                        f"{self.base_url}/"
                        f"_apis/wit/workItems/"
                        f"{parent_task_id}"
                    ),
                    "attributes": {
                        "comment": (
                            "Bug created using "
                            "Azure Bug Reporter"
                        )
                    }
                }
            },

            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "AttachedFile",
                    "url": attachment_url,
                    "attributes": {
                        "comment": (
                            "Screenshot captured "
                            "using Azure Bug Reporter"
                        )
                    }
                }
            }
        ]

        headers = self.headers.copy()

        headers["Content-Type"] = (
            "application/json-patch+json"
        )

        response = requests.post(
            url,
            headers=headers,
            json=patch_document,
            timeout=60
        )

        if not response.ok:

            raise RuntimeError(
                "Bug creation failed.\n\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text}"
            )

        return response.json()