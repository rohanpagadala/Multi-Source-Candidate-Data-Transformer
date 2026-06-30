from typing import Any, Dict, List, Optional
from pydantic import create_model, Field, ValidationError
from src.models import CanonicalProfile

# Mapping string types from config to python types
TYPE_MAPPING = {
    "string": str,
    "string[]": List[str],
    "number": float,
    "integer": int,
    "boolean": bool,
    "object": Dict[str, Any],
    "object[]": List[Dict[str, Any]]
}

def get_python_type(type_str: str) -> Any:
    return TYPE_MAPPING.get(type_str, Any)

def validate_projected_output(output: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Dynamically construct a validation schema based on config fields
    and validate the projected output against it.
    If no config is provided, validate against the default CanonicalProfile.
    """
    if not config or "fields" not in config:
        # Default validation against the canonical profile schema
        try:
            profile = CanonicalProfile(**output)
            return profile.model_dump()
        except ValidationError as e:
            raise ValueError(f"Canonical profile schema validation failed: {e}")

    # Build dynamic Pydantic model fields
    model_fields = {}
    fields_config = config.get("fields", [])
    
    for field_cfg in fields_config:
        path = field_cfg.get("path")
        type_str = field_cfg.get("type", "string")
        required = field_cfg.get("required", False)
        
        py_type = get_python_type(type_str)
        
        # If not required, it can be None (null)
        if not required:
            py_type = Optional[py_type]
            model_fields[path] = (py_type, None)
        else:
            model_fields[path] = (py_type, Field(...))

    # Add overall_confidence and provenance if toggled in config
    if config.get("include_confidence", True):
        model_fields["overall_confidence"] = (Optional[float], None)
        
    if config.get("include_provenance", False) or "provenance" in output:
        model_fields["provenance"] = (Optional[List[Dict[str, Any]]], None)

    # Create the dynamic Pydantic model
    DynamicModel = create_model("ProjectedOutput", **model_fields)

    try:
        validated_instance = DynamicModel(**output)
        return validated_instance.model_dump()
    except ValidationError as e:
        raise ValueError(f"Projected output validation failed. Errors:\n{e}")
