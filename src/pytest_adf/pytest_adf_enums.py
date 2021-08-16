from enum import Enum


class BlobEventType(str, Enum):
    """Specify supported blob event types of Azure Data Factory Trigger
    """

    BLOB_CREATED = "BlobCreated"
    BLOB_DELETED = "BlobDeleted"


class TriggerRunDataAPIAction(str, Enum):
    """Specify available api actions from event payload of a trigger-run
    """

    PUT_BLOB = "PutBlob"
    DELETE_BLOB = "DeleteBlob"
