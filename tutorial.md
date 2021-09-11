# Using BulkOps App
The below documentation outlines, the basic use cases of the app and how you can perform various operations. The feature includes the below

## Features
* Bulk creating Jira users or Jira Service Management customer users
* Bulk creation of Groups
* Bulk deletion of Groups
* Bulk Add users to groups (multiple users & groups)
* Bulk remove users from groups (multiple users & groups)
* Bulk delete Projects
* Bulk change Project leads
* Bulk delete issues 

## Use cases
### Cloud to cloud import of users
* User migration (cloud to cloud or even server to cloud or DC to cloud)? Yes, you can be able to use this app to perform not just the user creation but add those users to their rightful groups as well with the click of a button and using a CSV file to design your data. Check the app help menu to see the format to creating and adding users to multiple groups at the same time.

### Change of multiple project leads
* You can easily now change Project lead but we didn’t stop there, you can do this in bulk for multiple projects.

### Create Jira Service Management customers
* Not only can you create Jira users but you can create Jira Service Management customers properly with their display name.

### Deleting multiple users
* Let’s say you made a mistake during user import, fear not you can easily bulk delete those users.
* Likewise, if you have hundreds of users, you want remove from utilizing your licenses, this can also be done.

### Removing multiple users from group or simply add users to multiple groups
* Perform bulk operations of adding users to group or remove them at will.

### Deactivating multiple users
* The concept of deactivating a user, basically just means to remove the user from a group that has product access. So using the remove user from group feature, you can actually deactivate users.

### Deleting the nth number of issues
* You know when you want to bulk delete thousands of issues and you’re limited to 1K issues and the multiple clicks? Well, now all you just have to do is use a JQL that returns those thousands of issues and just delete all the way. (Please always make sure when using this, that you take the utmost care. If in doubt, do not press the submit button. Once it start, it can't be stopped.)


# HOW-TO
## Signup
![](https://github.com/princenyeche/BOP/blob/master/img/signup.png)

Once you load the app, you will need to create a user account for you to be able to sign in. Navigate to the signin page and register a user.

## Home 
![](https://github.com/princenyeche/BOP/blob/master/img/home_screen.png)

Once you've signed in, you can view the navigation menu or you can simply go straight to start using the app. The UI is pretty straight forward for navigation and anytime you're in doubt, click the "Need help" button to get the answer to any F.A.Q's

## Configuration
![](https://github.com/princenyeche/BOP/blob/master/img/config_screen.png)

The configuration page helps you to input your API token, it has a status bar to alert you if the token is active or inactive. Click the "Edit token" button and place your Atlassian API token. Also you can navigate to the "settings" page to change your instance URL.

## Bulk Creation of Group
![](https://github.com/princenyeche/BOP/blob/master/img/bulk_create_groups.png)

Creating multiple groups is easy. Simply navigate to the create groups under the "Groups" button. Key in multiple group names separated by comma to begin.

## Bulk Add users to Group
![](https://github.com/princenyeche/BOP/blob/master/img/bulk_add_users_to_groups.png)

This feature requires you upload a csv file, click the "Need help" button to see an example of the csv file format. Once ready, simply upload the file.

## Audit log
![](https://github.com/princenyeche/BOP/blob/master/img/audit_log.png)

Keep track of everything you're doing by visiting the audit log to see what changes has been done or what failed.


# Support
* Please report any bugs or issues by raising a **[Support ticket](https://elfapp.website/support)** or if you have questions.
