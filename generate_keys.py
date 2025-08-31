# Environment configuration for PythonAnywhere
import secrets


# Generate secure secret keys (run this once to generate keys, then use the generated keys)
def generate_secret_keys():
    secret_key = secrets.token_urlsafe(32)
    refresh_secret_key = secrets.token_urlsafe(32)
    print(f"SECRET_KEY={secret_key}")
    print(f"REFRESH_SECRET_KEY={refresh_secret_key}")


if __name__ == "__main__":
    generate_secret_keys()
