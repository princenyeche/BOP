# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)


## v4.1.3 - (9 February 2023)
## Updates and Patch
* [Snyk] Security upgrade python from 3.10.8-slim-bullseye to 3.12.0a3-slim-bullseye
* Made changes to flash messages 
* Dependency update 
* Updated versioning files


## v4.1.2 - (20 January 2023)
## Updates and Patch
* Fixed issue with email link not appearing when delivered to Microsoft email systems
* Dependency update 
* Updated versioning files


## v4.1.1 - (16 December 2022)
## Updates and Patch
* Added CSRF error handler 
* Changed email template from plain text to HTML 
* Dependency update 
* Heroku runtime update to 3.8.16


## v4.1.0 - (30 November 2022)
## Patch and update
* [Snyk] Security upgrade python from 3.8-slim-buster to 3.10.8-slim-bullseye
* [Snyk] Security upgrade setuptools from 39.0.1 to 65.5.1
* Documentation update


## v4.0.9 - (16 November 2022)
## Patch and update
* Updated Heroku python runtime #479
* Updated support option icon colours


## v4.0.8 - (16 November 2022)
## Patch and update
* Dependency update


## v4.0.7 - (29 October 2022)
## Patch and update
* Dependency update


## v4.0.6 - (16 September 2022)
## Patch and update
* Dependency update
* Changed Heroku runtime environment to 3.8.14
* Security update on dependency mako


## v4.0.5 - (13 August 2022)
## Update
* Dependency update
* Added a robot header to frontend page
* Changed Heroku runtime environment to 3.8.13


## v4.0.4 - (10 July 2022)
## Update
* Dependency update
* Added potential fix to inform more information on 400 errors on bulk deletion.
  * Introduced a new function called `truncate` which helps in reducing the activity column text prior to saving to DB.
  

## v4.0.3 - (22 June 2022)
## Update
* Dependency update
* Rewrote exceptions on bulk upload into a function called `capture_exceptions`
* Added error message when a single record is used for bulk operation.


## v4.0.2 - (25 May 2022)
## Update
* Dependency update


## v4.0.1 - (12 April 2022)
## Update
* Dependency updates
* Fix to `filter_jsm` function


## v4.0.0 - (23 December 2021)
## Update
* Bump dependency for Jiraone to v0.4.8
* Changed input forms to text forms for create and remove group features
* Added JSM features for cloud migrations
* Added new FAQ data.
* Bump BulkOps app for Jira to v4.0.0 making it a complete cloud migration tool. You can now perform all migrations for user management from server, datacenter or another cloud environment to Atlassian cloud instances.


## v3.8.7 - (28 October 2021)
## Update
* Added a clear task feature - The ability to clear pending jobs from the audit page.
* Dependency update


## v3.8.6 - (28 September 2021)
## Update
* Dependency update

## v3.8.5 - (11 September 2021)
### Update
* Added column validations for uploaded file. Users will need to upload the right format of expected columns for bulk operation.
* Added the ability to create users and add the users to multiple groups.
* Added the ability to add users to multiple groups and remove users from multiple groups. This way, you can now remove a user from groups or add to groups at the same time.


## v3.5.7 - (22 July 2021)
### Update
* Validation update on form URLs 

## v3.5.6 - (9 July 2021)
### Update
* minor patches
* remove unused f string

## v3.5.5 - (8 July 2021)
### Update
* Corrected auto deploy variable
* Added more variables to `app.json` file
* Added new variable to control queue time out.

## v3.5.2 - (10 June 2021)
### Update
* Added a confirmation feature to validate email address upon sign up
* Added a means to resend confirmation email in the event the user didn't receive it.
* Updated dependencies.


## v3.0.0 - (16 May 2021)
### Update
* Corrected unnecessary capitalization of text on frontend UI.
* Added a `goodbye message` when a user account is deleted.

## v2.0.8 - (13 April 2021)
### Update
* Added a timeout function, so when a user is inactive for 10 mins the system logs them out.
* You can't be able to change instance url as it's made into read only


## v2.0.7 - (29 January 2021)
### Update
* rewrote directory creation into functions
* rewrote JSD to JSM inline with new changes by Atlassian
* corrected few text grammer.

### Fixed
* Fixed bulk delete issue - now it's possible to delete > 1K issues at a time
* Issue with 401 error with bulk user feature when less than 10 users.

## v2.0.6 - (10 January 2021)
### Update
* Removed `JiraUsers` Class
* removed unused f string.

### Added
* Added `jiraone` module to handle the Authentication and API endpoints.

## v2.0.5 - (29 December 2020)
### Update
* Removed auth_request and headers from global variables in `JiraUsers` Class
* Removed staticmethods in `JiraUsers` Class

### Added
* Added `auto_commit` and `auto_commit_jobs` functions to avoid duplicated statements for `Audit` request
* Added a flash message to be displayed if token is invalid in any bulk process.

### Fixed
* Bulk Project lead always fails with 401 because there was no active session for it to work

## v2.0.4 - (10 December 2020)
### Added
* Automate notifications for Admin users

## v2.0.3 - (07 December 2020)
### Added
* Added a welcome `email` and `message` notifications for new sign ups

## v2.0.2 - (05 December 2020)
### Added
* Added a notification system for BulkOps Jobs

### Update
* updated the version text file to a none extension file `VERSION`
* edited the `README` file

## v2.0.1 - (23 October 2020)
### Update
* Updated variables for flash messages
* updated frontend when logging in to use only small letters during sign up / signin

## v2.0.0 - (21 October 2020)

### Added
* changed min. character for password to 8
* Added Running Jobs Class using redis
* Rewrote variable names in small letters
* Added requests object to JiraUsers Class
* Added new functions for worker task

### Removed
* Rewrote Audit class expression to account for any unknown bugs if using on different servers
* Removed flash messages for bulk changes, changes will be viewable from the audit log pages

### Fixed
* Issue with timeout error on bulk changes fixed

## v1.2.5 - (28 September 2020)

### Removed
- Remove `passive_deletes=True` in `User class` on `database.py` file - According to the [SQLAlchemy Doc](https://docs.sqlalchemy.org/en/13/orm/cascades.html?highlight=cascade#delete) the usage should be as changed now. Somehow I must have mixed this up during implementation, only noticed this caused a problem in some DB relationship. will run further test to confirm this fixes it fully. For now going to commit these changes.

## v1.2.4 - (28 September 2020)
### Added
- issue with Flask_SQLAlchemey , SQLAlchemy and Alembic
- issue doesn't allow commit to work for transaction tables, had to bump up the versions for each module.
- read the respective module to get more details on the issue and see `requirements.txt` file for changes.

## v1.2.3 - (25 September 2020)
### Added
- account deletion of file to remove single directory
- added a defined session name for the BulkOps App.

## v1.2.2 - (19 September 2020)
### Added
- Updated the read me file and added the DB init on local installation

## v1.2.1 - (20 August 2020)
### Added
- Updated the version variable on the config file

## v1.2 - (20 August 2020)
### Added
- Added a Progress function to visualize the progress of the request.
- Added category to the Alert flash messages on the signup and signin pages.

## v1.1 - (8 August 2020)
### Problem
- Noticed that the Message id could be changed from the URL and another user's message could be read

### Fixed
- Applied a fix to separate both instances of reading received messages and sent messages by current user.

## v1.0 - (6 August 2020)
### Added
- Bulk Operations App Initial Release. This App is a Jira Cloud App and helps with Bulk Operations of certain Admin functionalities.
- There's no progress bar to let you know the status of an operation. I have not found an efficient way to go about it. I will update this App once I have the time to do so.
