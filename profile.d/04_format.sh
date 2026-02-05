# Function: json_escape
# Description: Escapes a string for safe inclusion in JSON
# Usage: escaped=$(json_escape "$input")
# Parameters:
#   $1 - The input string to escape
# Returns:
#   The JSON-escaped string via stdout
# Function: json_escape
# Description: Escapes a string for safe inclusion in JSON
# Usage: escaped=$(json_escape "$input")
function json_escape() {
    local input="$1"
    local escaped=""
    local i=0
    local char
    
    # Process each character
    while [ $i -lt ${#input} ]; do
        char="${input:$i:1}"
        case "$char" in
            '"')  escaped="${escaped}\\\""
                ;;
            \\) escaped="${escaped}\\\\"
                ;;
            '/')  escaped="${escaped}\/";;
            $'\b') escaped="${escaped}\\b";;
            $'\f') escaped="${escaped}\\f";;
            $'\n') escaped="${escaped}\\n";;
            $'\r') escaped="${escaped}\\r";;
            $'\t') escaped="${escaped}\\t";;
            *) 
                # Check if character is a control character (ASCII 0-31)
                if [ "$(printf '%d' "'$char")" -lt 32 ]; then
                    # Convert to \uXXXX format
                    printf -v hex '%04x' "$(printf '%d' "'$char")"
                    escaped="${escaped}\\u${hex}"
                else
                    escaped="${escaped}${char}"
                fi
                ;;
        esac
        i=$((i + 1))
    done
    
    printf '%s' "$escaped"
}