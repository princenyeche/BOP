# **Bulk Operations App**
Bulk Operations App for Jira is a Cloud based Add-on, which helps in performing Bulk operational features not available on Jira Cloud. 
![](https://github.com/princenyeche/BOP/blob/master/img/bulkops.png)
### **Features**
* Bulk creating Jira users or Jira Service Desk users
* Bulk creation of Groups
* Bulk deletion of Groups
* Bulk Add users to groups (multiple users & groups)
* Bulk remove users from groups (multiple users & groups)
* Bulk delete Projects
* Bulk change Project leads
* Bulk delete issues [**experimental**]


## **Configuration**
You can be able to launch the application in various ways. either you host it yourself or you can easily run it locally on your machine or download it from Atlassian Marketplace and run it on your Cloud Instance. 

## **Hosting with Linux**
### Cpanel Linux
You can use any Linux environment that support or has the ability to install python modules and the required WSGI needed to run the App. Our recommendation is to use a web hosting service that provides CPanel as it comes preconfigured with `Passenger` WSGI which can be set up within less than 5 mins. Go to Cpanel and find Setup python App.

![](https://github.com/princenyeche/BOP/blob/master/img/setup.png)

##### Create an App by clicking on the "Create Application" button

![](https://github.com/princenyeche/BOP/blob/master/img/create_app.png)
Then, click to edit the App, set your "Application Start file" as `startup.py` and "Application Entry point" as `bulk`. Therefore your `passenger_wsgi.py` file should look like the below:
```python
import imp
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

wsgi = imp.load_source('wsgi', 'startup.py')
application = wsgi.bulk
```
SSH into your Application path using the virtualenv and run the `pip install -r requirements.txt` file to install all the required modules.

In the environment variables, you will need to set it up as below, so python knows what to use anytime you stop or start the Application.
| <!-- -->    | <!-- -->    |
|-------------|-------------|
|DATABASE_URL  | mysql+pymysql://youruser:yourpassword@localhost:3306/yourdatabase|
|FLASK_APP| startup.py|
|MAIL_SERVER | smtp.example.com |
|MAIL_PORT | 587 |
|MAIL_USE_TLS | 1 |
|MAIL_USERNAME | youremail@example.com|
|MAIL_PASSWORD | yourpassword |
|MAIL_SUFFIX | example.com  |
|SECRET_KEY | secretkey |  

### Heroku
Heroku is an easier hosting platform which you can get for free to host this App, simply create an Account at **[Heroku](https://heroku.com)**, configure and provide python as your framework and you can easily have your own App running in no time. Assuming you've already logged in to Heroku on your terminal.
```bash
# create our App folder
mkdir App && cd App
# make a virtual env so we can have pip
virtualenv venv
. venv/bin/activate
# clone the repo
git clone https://github.com/princenyeche/BOP.git
cd BOP
# a Procfile is already included
git status
# Add the files which includes Procfile, startup.py, bulkops folder
git add Procfile, startup.py, <bulkops folder>
git commit
# create a heroku app, the below makes a default url
heroku create
heroku addons:create heroku-postgresql:hobby-dev
git push heroku master
```
Your `requirements.txt` file should download all the necessary modules needed by Python framework on Heroku. The Procfile is needed by Heroku to start up the Application, one is already available for this App. Don't forget to go to your **Heroku App > Settings > Reveal Configs vars** and set up the environment variables as shown on the table above. your DATABASE_URL should be configured for you from the above command.

### Local
Make sure Python is installed! Goto https://www.python.org/downloads/ any version from v3.x will do. You will also need to ensure you have PIP on your computer with the download. check by using 
```bash
$: pip --version
```

If you installed Python from source, with an installer from python.org, or via [Homebrew](https://brew.sh/) you should already have pip. If you’re on Linux and installed using your OS package manager, you may have to [install pip](https://pip.pypa.io/en/stable/installing/) separately.

This is the most easiest way to have this App, by running it locally on your device. use the `requirements.txt` file to ensure you have all the modules installed on your machine.
```python
pip install -r requirements.txt
```
you will also need to export some important variables in order to get the App running in flask. Open your terminal (linux/macOS) and key in the below variables
```bash
export FLASK_APP=bulkops
export FLASK_ENV=development
```
if you're on `windows` OS, please use `SET` command
```powershell
SET FLASK_APP=bulkops
SET FLASK_ENV=development
```
#### Providing Mail Support
In order for you to get the mail running while local, you will need to export the variable on terminal or use `SET` command for windows users.
```bash
export MAIL_SERVER=smtp.example.com
export MAIL_PORT=587
export MAIL_USE_TLS=1
export MAIL_USERNAME=youremail@example.com
export MAIL_PASSWORD=yourpassword
export MAIL_SUFFIX=example.com
```
#### Starting up the App
Once you're done with the configuration, you can load up the App by running the below command
```bash
flask run
```
if you would like to run the App on another IP or port local to you, you can specify the host and port number, so it can be access locally on your network. find your local machine IPv4 address to find your IP, use the `ifconfig` (linux/macOS) or `ipconfig` if on windows.
```bash
flask run -h 192.168.1.100 -p 8080
```
