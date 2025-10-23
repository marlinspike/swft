@echo off
echo Installing vulnerable dependencies for CVE testing...

cd /d "c:\Dev\scai\python"

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing core vulnerable packages...
python -m pip install fastapi==0.68.0
python -m pip install jinja2==2.11.0
python -m pip install markupsafe==1.1.1
python -m pip install flask==1.1.4
python -m pip install pydantic==1.8.2
python -m pip install requests==2.25.1
python -m pip install urllib3==1.26.5
python -m pip install uvicorn==0.15.0
python -m pip install click==7.1.2
python -m pip install werkzeug==1.0.1
python -m pip install setuptools==65.5.0
python -m pip install django==3.1.14

echo Installing additional dependencies...
python -m pip install python-dotenv pytest pytest-cov httpx

echo.
echo Installation complete!
echo Run "trivy fs --severity HIGH,CRITICAL ." to scan for vulnerabilities
pause