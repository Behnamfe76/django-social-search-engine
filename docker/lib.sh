# Shared helpers for the container entry points.

# Mirrors env_bool() in settings.py, so a variable spelled "true", "1", "yes" or
# "on" means the same thing on both sides of the process boundary.
is_true() {
    case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
        1 | true | yes | on) return 0 ;;
        *) return 1 ;;
    esac
}
