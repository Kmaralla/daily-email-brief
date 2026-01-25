from setuptools import setup, find_packages

setup(
    name="daily-email-brief",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-auth==2.23.4",
        "google-auth-oauthlib==1.1.0",
        "google-auth-httplib2==0.1.1",
        "google-api-python-client==2.108.0",
        "openai==1.3.7",
        "click==8.1.7",
        "python-dotenv==1.0.0",
        "keyring==24.3.0",
        "flask==3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "daily-brief=src.ui.cli:cli",
        ],
    },
)
