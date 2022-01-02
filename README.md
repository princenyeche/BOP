[![Codacy Badge](https://app.codacy.com/project/badge/Grade/6068ebb9b8794d11bcb8471f71b711c6)](https://www.codacy.com/gh/princenyeche/BOP/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=princenyeche/BOP&amp;utm_campaign=Badge_Grade) [![Requirements Status](https://requires.io/github/princenyeche/BOP/requirements.svg?branch=master)](https://requires.io/github/princenyeche/BOP/requirements/?branch=master)
[![Build Status](https://app.travis-ci.com/princenyeche/BOP.svg?branch=master)](https://app.travis-ci.com/princenyeche/BOP)

# **Bulk Operations App**
Bulk operations app for Jira is a cloud based addon, which helps in performing bulk operational features not available on Jira cloud. 
![](https://github.com/princenyeche/BOP/blob/master/img/bulkops.png)
## **Features**
  * Bulk create users Jira users or Jira Service Management users
  * Bulk delete Jira users or delete Jira users or Jira Service Management users
  * Bulk creation of groups
  * Bulk deletion of groups
  * Bulk add users to groups (multiple users & groups)
  * Bulk remove users from groups (multiple users & groups)
  * Bulk delete projects
  * Bulk change project leads
  * Bulk delete issues
  * Bulk creation of JSM organizations.
  * Bulk deletion of JSM organizations.
  * Bulk add a JSM organizations to a service desk.
  * Bulk remove a JSM organizations from a service desk.
  * Bulk addition of customers into JSM organization.
  * Bulk removal of customers from JSM organization.
  * Bulk addition of customers to specific JSM projects e.g. ITSM or SD
  * Bulk removal of customers from specific JSM projects e.g. ITSM or SD

## **Configuration**
You can be able to launch the application in various ways. Either you host it yourself or you can easily run it locally on your machine or download it from **[Atlassian Marketplace](https://marketplace.atlassian.com/apps/1223196/bulkops-app?hosting=cloud&tab=support)** and run it on your cloud instance. 

   * Check out the online version of bulkOps app **[here](https://elfapp.website/bulkops)**

## **Tutorials**
   * Please see the tutorials on how to use this app **[here](https://github.com/princenyeche/BOP/blob/master/tutorial.md)**

## **Hosting**

### Heroku
Heroku is an easier hosting platform which you can get for free to host this app. Simply create an account at **[Heroku](https://heroku.com)**, configure and provide python as your framework and you can easily have your own app running in no time. Assuming you've already logged in to Heroku on your terminal. You need to have git, if you don't, download it. If on macOS use "homebrew", for windows use **[Git for Windows](https://git-for-windows.github.io)**

You can use the below methods to deploy to heroku

#### Using the deploy button
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/princenyeche/BOP)

Remember to add a mail support variable as it is required to send you verification link during the app configuration. The names of the environment variables are provided below, so update the mail attributes with your own details. Once that is done, please scale up the redis worker using `heroku ps:scale worker=1 -a "app_name"` from your terminal or from the Heroku UI app console.

#### Using a shell script
- Deploy by running the `run_setup.sh` file located in the `BOP` root folder

#### Signup and configure heroku yourself
```bash
# create our app folder
mkdir app && cd app
# clone the repo
git clone https://github.com/princenyeche/BOP.git
cd BOP
# a procfile is already included
git status
# create a heroku app, the below makes a default url
heroku create <give appname>
# add a buildpack
heroku buildpacks:set heroku/python -a <appame>
# Add the files which includes Procfile, startup.py, bulkops-folder
git add Procfile startup.py requirements.txt <bulkopsfolder>
git commit -m "commits"
heroku addons:create heroku-postgresql:hobby-dev -a <appname>
# add redis add-on
heroku addons:create heroku-redis:hobby-dev -a <appname>
git push heroku master
```
Your `requirements.txt` file should download all the necessary modules needed by python framework on Heroku. The procfile is needed by Heroku to start up the application, one is already available for this app. Don't forget to go to your **Heroku App > Settings > Reveal Configs vars** and set up the environment variables as shown on the table below. your DATABASE_URL should already be configured for you from the above command.

In the environment variables, you will need to set it up as below, so python knows what to use anytime you stop or start the application.
| <!-- -->    | <!-- -->    |
|-------------|-------------|
|DATABASE_URL  | postgres://youruser:yourpassword@remotehost:5487/yourdatabase|
|FLASK_APP| startup.py|
|MAIL_SERVER | smtp.example.com |
|MAIL_PORT | 587 |
|MAIL_USE_TLS | 1 |
|MAIL_USERNAME | youremail@example.com|
|MAIL_PASSWORD | yourpassword |
|MAIL_SUFFIX | example.com  |
|ADMINS      | no-reply@example.com |
|CONTACT_EMAIL | admin@example.com |
|SECRET_KEY | secretkey |  
|SECURITY_SALT | anothersecretkey | 
|QUEUE_TIMEOUT | 1h | 
|REDIS_URL | redis://url |
|MAX_CONTENT_LENGTH| 2 * 1024 * 1024 |
|SUPPORT_LINK| https://example.com|

If redis is installed, use the terminal and activate it by using `heroku ps:scale worker=1 -a <app_name>` to provision the redis worker on the application(P/s To install redis plugin on Heroku requires you to add a payment system to your account if not you cannot use it). The `queue_timeout` environment variable is a string and can be represented as "30m" or "1h", "2h" etc. This tells bulkops how long a request job can run for using redis. This job is a queue task that is submitted and update back to the user.

### Local
Make sure python is installed! Goto https://www.python.org/downloads/ any version from v3.6.x and above will do. You will also need to ensure you have `pip` on your computer with the download. Check by using 
```bash
pip --version
```

You can also run the `run_setup.sh` file located in the `BOP` folder to install the app on your device automatically. 

If you installed python from source, with an installer from python.org, or via [Homebrew](https://brew.sh/) you should already have pip. If you’re on Linux and installed using your OS package manager, you may have to [install pip](https://pip.pypa.io/en/stable/installing/) separately.

This is the most easiest way to have this app, by running it locally on your device. Use the `requirements.txt` file to ensure you have all the modules installed on your machine.
```bash
pip install -r requirements.txt
```
OR
```bash
python3 -m pip install -r requirements.txt
```
you will also need to export some important variables in order to get the app running in flask. Open your terminal (linux/macOS) and key in the below variables
```bash
export FLASK_APP=startup.py
export FLASK_ENV=development
```
if you're on `windows` OS, please use `SET` command
```powershell
SET FLASK_APP=startup.py
SET FLASK_ENV=development
```
#### Providing Mail Support
For you to get the mail running locally, you will need to `export` the variable on terminal or use `SET` command for windows users.
```bash
export MAIL_SERVER=smtp.example.com
export MAIL_PORT=587
export MAIL_USE_TLS=1
export MAIL_USERNAME=youremail@example.com
export MAIL_PASSWORD=yourpassword
export MAIL_SUFFIX=example.com
export ADMINS=no-reply@example.com
```

#### Initialize the database
You will need to start up the database during initial setup, else the app will result in an error. Run the below commands sequentially to begin.
```bash
flask db init
flask db migrate
flask db upgrade
```

#### Starting up the app
Once you're done with the configuration, you can load up the app by running the below command
```bash
flask run
```
OR simply use
```bash
python startup.py
```

If you would like to run the app on another IP or port local to you, you can specify the host and port number. So it can be accessed locally on your network. Find your local machine IPv4 address by using the `ifconfig` (linux/macOS) or `ipconfig` if on windows.
```bash
flask run -h 192.168.1.100 -p 8080
```

#### Using Redis Worker
Using redis locally, download the software. On macOS use `brew install redis`. Once installed start the service automatically by using `brew services start redis`. Which will enable the app listen for Jobs. You can view these jobs by running on terminal `rq worker bulkops-jobs`.

### Using Docker
Ensure you have [Docker setup for your respective operating system](https://docs.docker.com/get-docker/).

Run the following from the BOP project folder root
1. `docker build -t bulkops-app .` 
2. `docker run -p 5000:5000 bulkops-app`

On point 1, notice the dot at the end, it is required to successfully build the docker image. Once that it completed, use the second command to run the image locally on docker. If you need to use a different port, you can modify the `Dockerfile` and the `runit.sh` file for you to have the app expose to your network. The app requires a mail configuration for email delivery. Ensure that you export all the required environment variables prior to building the docker image. You can do this by putting the variables in the `runit.sh` file prior to building it. 

Do not export secrets on the container, see this documentation on [Managing secrets data with Docker secrets](https://docs.docker.com/engine/swarm/secrets/)

### Other Linux Hosting
* You can use other linux servers as well to install this application online.

## SECURITY
(If using the online version from Atlassian Marketplace)
* Since you're accessing your instance, always make sure you protect your password
* You can change the API token to "None" after usage, so the connection to your instance is inactive.
* Activate the **Notify me when I login** feature.

## LICENSE
I hope this is clear but if it isn't, please note this software uses **[MIT License](https://github.com/princenyeche/BOP/blob/master/LICENSE)**
