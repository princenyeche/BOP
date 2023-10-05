#!/usr/bin/env bash
# This shell script can be executed to install the app locally or to Heroku
# response returned
FAIL=1
SUCCESS=0

function systemCheck() {
  # check if python 3 is available
  PYENV=$(python -c"import sys; print(sys.version_info.major)") || $(python3 -c"import sys; print(sys.version_info.major)")
  if [[ $PYENV -eq 2 ]]; then
     printf 'Checking python version. \n'
     printf 'Python version is lesser than 3, please upgrade and try again. \n'
     createInstallFolder
     exit $SUCCESS
   elif [[ $PYENV -eq 3 ]]; then
     echo "Detected python version ${PYENV}"
     # create our app folder
     createInstallFolder
  fi
}

function checkbrew() {
  checkBrew=$(which brew)
   if [[ $checkBrew == "/usr/local/bin/brew" ]]; then
      echo "Brew is installed for $machine"
    else
      echo "Brew not found, please install it."
      echo 'run: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" to install brew'
      read -rp "Do you want to install brew?: (y/n)" askinstall
      if [[ $askinstall == "y" || $askinstall == "Y" ]]; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      else
        echo "No action taken"
        exit $SUCCESS
      fi
         $0
      exit $SUCCESS
   fi
}

# system check to determine type of machine
systemName="$(uname -s)"
case "${systemName}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${systemName}"
esac
echo "Detected device running on ${machine}"

# recommend common commands to run
makeInstall() {
   if [[ $machine == "Linux" ]]; then
       echo "installing $1"
       sudo apt get install "$1" || sudo yum install "$1"
   elif [[ $machine == "Mac" ]]; then
      echo "installing $1"
      checkbrew
      brew install "$1" || brew tap brew/"$1"
     fi
}

createInstallFolder() {
  mkdir App
  cd App || { echo "Failure"; exit $FAIL;}
}

function runError {
  # error checking
  if [[ "$?" -eq "$SUCCESS" ]]; then
    if [[ $machine == "Linux" ]]; then
      echo "Use your package manager to download $1"
      makeInstall "$@"
    elif [[ $machine == "Mac" ]]; then
      echo "Use your brew to download $1."
      makeInstall "$@"
    elif [[ $machine == "Cygwin" || $machine == "MinGw" ]]; then
      echo "Use google to download $1 for windows device"
    elif [[ $machine == "UNKNOWN:${systemName}" ]]; then
      echo "Use google please, to search for $1"
    fi
  fi
}

function runHeroku {
  read -rp "Enter a name for your Heroku app: " app_name
  if [[ "$app_name" == null ]]; then
      echo -n "Parameter for Heroku app name is missing."
      exit $FAIL
  else
    heroku create "$app_name"
    # add a buildpack
    git config --global user.email "$app_name"
    git config --global user.name "$app_name"

    heroku buildpacks:set heroku/python -a "$app_name"
    # git push heroku main
    # Add the files which includes Procfile, startup.py, bulkops-folder
    git add Procfile startup.py requirements.txt bulkops
    heroku addons:create heroku-postgresql:hobby-dev -a "$app_name"
    # add redis add-on
    # please note that you will need to verify your account to have redis installed
    read -rp "Please note that you will need to verify your heroku account to have redis installed. Do that before proceeding. (press any key to continue)" caution
    heroku addons:create heroku-redis:hobby-dev -a "$app_name"
    read -rp "Do you want to push the app to the repo?" askpush
     if [[ $askpush == "Y" || $askpush == "y" ]]; then
       git commit -m "commits $2"
        git push heroku master
        python3 -mwebbrowser https://dashboard.heroku.com/apps/"${app_name}"/settings
        else
          echo "No action taken. Run the '$0' if you want to continue"
          exit $SUCCESS
       fi

  fi
}

# run flask if locally
function installBop {
  flask db init
  sleep 1
  flask db migrate
  sleep 1
  flask db upgrade
}

function initializeBop {
 flask run
}

# check if pip is installed
function checkPip() {
  if [[ $VIRTUAL_ENV == "" ]]; then
    echo "You are not in a virtual environment yet."
    read -rp "Enter the path to your virtual environment (e.g. must end in venv folder): " env_path
    present_dir=$(pwd)
    checkpath=$(echo "$env_path" | sed 's/ /\\/g' | sed 's/\\/\\ /g')
    echo "$checkpath"
    cd "$checkpath" || exit
    source bin/activate
    echo "Switching to virtual environment..."
    sleep 1
    cd "$present_dir" || exit
  fi
}

# ask which installation is needed
read -rp "Do you want to install locally or to heroku? (options L or H): " ask
if [[ $ask == "L" || $ask ==  "l" ]]; then
  echo "Installing locally..."
  systemCheck
  checkPip
  checkGit=$(which git)
  if [[  $checkGit == "/usr/local/bin/git" || $checkGit == "/opt/homebrew/bin/git" ]]; then
    git clone https://github.com/princenyeche/BOP.git
    cd BOP || { echo "Failure"; exit $FAIL;}
    echo "Installing dependencies for the app..."
    pip install -r requirements.txt
    export FLASK_APP=startup.py
    export FLASK_ENV=development
    installBop
    initializeBop
    else
      echo "Git not installed"
      runError "git"
    fi
elif [[ $ask == "H" || $ask ==  "h" ]]; then
systemCheck
echo "Checking, if heroku is available"
# clone the repo
checkGit=$(which git)
checkHeroku=$(which heroku)
if [[  $checkGit == "/usr/local/bin/git" || $checkGit == "/opt/homebrew/bin/git" ]]; then
  git clone https://github.com/princenyeche/BOP.git
  cd BOP || { echo "Failure"; exit $FAIL;}
  # a Procfile is already included with the download
  if [[ $checkHeroku == "/usr/local/bin/heroku" || $checkHeroku == "/opt/homebrew/bin/heroku" ]]; then
      # initiate a login via heroku
      heroku login
      # create a heroku app, the below makes a default url
      runHeroku "$@"
  else
      echo "Heroku is not installed on your $machine."
      read -rp "Do you want to install heroku on your $machine (Enter Y or N) to proceed:" answer
      if [[ "$answer" == "Y" || "$answer" == "y" ]]; then
        if [[ ! $checkHeroku == "/usr/local/bin/heroku" || ! $checkHeroku == "/opt/homebrew/bin/heroku" ]]; then
         runError "heroku"
         # if heroku is now available run the commands
         if [[ $checkHeroku == "/usr/local/bin/heroku" || $checkHeroku == "/opt/homebrew/bin/heroku" ]]; then
           runHeroku "$@"
         fi
        fi
      elif [[ "$answer" == "N" || "$answer" == "n" ]]; then
         printf 'Exiting request, we cannot proceed \n'
      else
        printf 'We do not understand the request.\n'
        fi
  fi
else
  echo "Git is not installed on your $machine."
  runError "git"
fi
else
  echo "Unable to understand option"
  exit $SUCCESS
fi
