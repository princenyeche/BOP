# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

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
