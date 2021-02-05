# Using BulkOps App
The below documentation outlines, the basic use cases of the App and how you can perform various operations. The feature includes the below

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
### Cloud to Cloud Import of Users
* User Migration (Cloud to Cloud)? Yes, you can be able to use this App to perform not just the user creation but add those users to their rightful groups as well with the click of a button and using a CSV file to design your data.

### Change of Multiple Project Leads
* You can easily now change Project lead but we didn’t stop there, you can do this in bulk for multiple projects.

### Create Jira Service Management Customers
* Not only can you create Jira users but you can create Jira Service Management customers properly with their display Name.

### Deleting multiple Users
* Let’s say you made a mistake during user import, fear not you can easily bulk delete those users.
* Likewise, if you have hundreds of users, you want remove from utilizing your licenses, this can also be done.

### Removing Multiple users from Group or Simply Add Users to Multiple groups
* Perform bulk operations of adding users to group or remove them at will.

### Deactivating Multiple Users
* The concept of deactivating a user, basically just means to remove the user from a group that has product access. So using the remove user from group feature, you can actually deactivate users.

### Deleting the nth number of issues
* You know how when you want to bulk delete thousands of issues and you’re limited to 1K issues and the multiple clicks. well now all you just have to do is use a JQL that returns those thousands of issues and just delete all the way. (please always make sure when using this, that you take the utmost care, if in doubt you can navigate away from the page to stop the process)


# HOW-TO
## Signup
![](https://github.com/princenyeche/BOP/blob/master/img/signup.png)

Once you load the App, you will need to create a user account for you to be able to sign in. Navigate to the signin page and register a user.

## Home 
![](https://github.com/princenyeche/BOP/blob/master/img/home_screen.png)

Once you've signed in, you can view the Navigation menu or you can simply go straight to start using the App. The UI is pretty straight forward for navigation and anytime you're in doubt, click the Need help button to answer any F.A.Q's

## Configuration
![](https://github.com/princenyeche/BOP/blob/master/img/config_screen.png)

The Configuration page helps you to input your API token, it has a status bar to alert you if the token is active or inactive. Click the "Edit token" button and place your Atlassian API token. Also you can navigate to the "Settings" page to change your Instance URL.

## Bulk Creation of Group
![](https://github.com/princenyeche/BOP/blob/master/img/bulk_create_groups.png)

Creating multiple groups is easy. Simply navigate to the Create groups under the "Groups" button. Key in multiple group names separated by comma to begin.

## Bulk Add users to Group
![](https://github.com/princenyeche/BOP/blob/master/img/bulk_add_users_to_groups.png)

This feature requires you upload a csv file, click the Need help button to see an example of the csv file format. once ready, simply upload the file.

## Audit log
![](https://github.com/princenyeche/BOP/blob/master/img/audit_log.png)

Keep track of everything you're doing by visiting the Audit log to see what changes has been done or what failed.


# Support
* Please report any bugs or issues by raising a **[Support ticket](https://elfapp.website/support)** or if you have questions.
