import re
from typing import Any, Dict, List, Optional
from src.models import CanonicalProfile
from src.normalization import normalize_phone, normalize_skill

def resolve_path(profile: CanonicalProfile, path: str) -> Any:
    """
    Resolve a path string (e.g. 'emails[0]', 'skills[].name', 'location.country')
    against a CanonicalProfile object.
    """
    # 1. Resolve dotted segments
    # Convert profile to dict to make path traversal easy
    data = profile.model_dump()
    
    parts = path.split('.')
    curr = data
    
    for i, part in enumerate(parts):
        if curr is None:
            return None
            
        # Check if the part contains an array index, e.g. emails[0]
        m_arr_idx = re.match(r'^(\w+)\[(\d+)\]$', part)
        if m_arr_idx:
            field, idx = m_arr_idx.groups()
            idx = int(idx)
            arr = curr.get(field) if isinstance(curr, dict) else getattr(curr, field, None)
            if isinstance(arr, list) and idx < len(arr):
                curr = arr[idx]
            else:
                return None
            continue
            
        # Check if the part maps an array, e.g. skills[]
        m_arr_map = re.match(r'^(\w+)\[\]$', part)
        if m_arr_map:
            field = m_arr_map.group(1)
            arr = curr.get(field) if isinstance(curr, dict) else getattr(curr, field, None)
            if not isinstance(arr, list):
                return None
            
            # If there is a subfield next (e.g. skills[].name)
            if i + 1 < len(parts):
                subfield = parts[i + 1]
                res = []
                for item in arr:
                    if isinstance(item, dict):
                        res.append(item.get(subfield))
                    else:
                        res.append(getattr(item, subfield, None))
                return res
            return arr

        # Simple field access
        if isinstance(curr, dict):
            curr = curr.get(part)
        else:
            curr = getattr(curr, part, None)
            
    return curr

def project_profile(profile: CanonicalProfile, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Project a CanonicalProfile into a custom output dictionary based on runtime config.
    """
    output = {}
    on_missing = config.get("on_missing", "null")  # null | omit | error
    
    fields_config = config.get("fields", [])
    if not fields_config:
        # Default projection: return full model_dump
        return profile.model_dump()
        
    for field_cfg in fields_config:
        path = field_cfg.get("path")
        from_path = field_cfg.get("from", path)
        required = field_cfg.get("required", False)
        normalize_type = field_cfg.get("normalize")
        
        # Resolve value from canonical profile
        val = resolve_path(profile, from_path)
        
        # Handle missing values
        if val is None or val == "" or val == []:
            if required:
                raise ValueError(f"Required field '{path}' is missing or empty.")
            
            if on_missing == "error":
                raise ValueError(f"Field '{path}' is missing and on_missing is set to 'error'.")
            elif on_missing == "omit":
                continue
            else: # null
                output[path] = None
                continue
                
        # Optional field normalization override at projection stage
        if normalize_type == "E164":
            if isinstance(val, list):
                val = [normalize_phone(p) for p in val if p]
            else:
                val = normalize_phone(str(val))
        elif normalize_type == "canonical":
            if isinstance(val, list):
                val = [normalize_skill(s) for s in val if s]
            else:
                val = normalize_skill(str(val))
                
        output[path] = val

    # Toggle overall confidence and provenance
    if config.get("include_confidence", True):
        output["overall_confidence"] = profile.overall_confidence
        
    if config.get("include_provenance", False) or "provenance" in [f.get("path") for f in fields_config]:
        # Dump provenance records
        output["provenance"] = [p.model_dump() for p in profile.provenance]
        
    return output
