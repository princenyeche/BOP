# Using BulkOps App
The below documentation outlines the basic use cases of the app and how to perform various operations. The feature includes the below

## Features
* Bulk creating Jira users or Jira Service Management customer users
* Bulk delete Jira users or Jira Service Management users
* Bulk creation of groups
* Bulk deletion of groups
* Bulk add users to groups (multiple users & groups)
* Bulk remove users from groups (multiple users & groups)
* Bulk delete projects
* Bulk change project leads
* Bulk delete issues 
* Bulk creation of JSM organizations.
* Bulk deletion of JSM organizations.
* Bulk addition of JSM organizations to a service desk.
* Bulk removal of JSM organizations from a service desk.
* Bulk addition of customers into JSM organization.
* Bulk removal of customers from JSM organization.
* Bulk addition of customers to specific JSM projects e.g. ITSM or SD
* Bulk removal of customers from specific JSM projects e.g. ITSM or SD

## Issues and troubleshooting
* [Troubleshooting BulkOps app for Jira](https://github.com/princenyeche/BOP/wiki/Troubleshooting-BulkOps-app-for-Jira)

## Articles 
* [BulkOps app for Jira articles](https://github.com/princenyeche/BOP/wiki/Articles-on-BulkOps-app-for-Jira)

## Use cases
### Cloud to cloud import of users
* User migration (cloud to cloud or even server to cloud or DC to cloud)? Yes, you can use this app to perform not just the user creation but add those users to their rightful groups with the click of a button; using a CSV file to design your data. Check the app help menu to see the format of creating and adding users to multiple groups at the same time.

### Deleting Jira users or customer user
* With the BulkOps app for Jira, you can delete Jira users or Jira Service Management customer only users. Simply upload your user record and delete those set of users.

### Change of multiple project leads
* You can easily change project lead but we didn’t stop there, you can do this in bulk for multiple projects.

### Create Jira Service Management customers
* Not only can you create Jira users but you can create Jira Service Management customers properly with their display name.

### Deleting multiple users
* Let’s say you made a mistake during user import, fear not as you can easily bulk delete those users.
* Likewise, if you have hundreds of users you want remove from utilizing your licenses, this can be done.

### Removing multiple users from group or simply add users to multiple groups
* Perform bulk operations of adding users to group or remove them at will.

### Deactivating multiple users
* The concept of deactivating a user, basically just means to remove the user from a group that has product access. So using the remove user from group feature, you can actually deactivate users.

### Deleting the n-th number of issues
* You know when you want to bulk delete thousands of issues and you’re limited to 1K issues and the multiple clicks? Well, now all you just have to do is use a JQL that returns those thousands of issues and just delete all the way. (Please always make sure when using this, that you take the utmost care. If in doubt, do not press the submit button.)

### Manage JSM organization users
* You can add users to JSM projects or organization and remove them from JSM project or organization. In addition, you can create or delete JSM organizations.


# HOW-TO
## Signup
![](https://github.com/princenyeche/BOP/blob/master/img/signup.png)

When you load the app, you need to create a user account to sign in. Navigate to the signin page and register a user. Please ensure when signing up, your email address must exist as a site-admin in the cloud instance that you sign up with. 

## Home 
![](https://github.com/princenyeche/BOP/blob/master/img/home_screen.png)

When you've signed in, you can view the navigation menu or simply go straight to start using the app. The UI is pretty straight forward for navigation and anytime you're in doubt, click the "Need help" button to get the answer to any F.A.Q's.

## Configuration
![](https://github.com/princenyeche/BOP/blob/master/img/config_screen.png)

The configuration page helps you to input your API token. It has a status bar to alert you if the token is active or inactive. Click the "Edit token" button and place your Atlassian API token. Also you can navigate to the "settings" page to change your instance URL.

## Bulk creating users and add to multiple groups
![](https://github.com/princenyeche/BOP/blob/master/img/create_add_group.png)

The above file format is required when creating Jira users and adding them to multiple groups during creation using your CSV file. You need to use this character `~>` as a delimiter between each group. Simply upload the file once done and your users will be created and added into the specified groups.

## Bulk creation of group
![](https://github.com/princenyeche/BOP/blob/master/img/bulk_create_groups.png)

Creating multiple groups is easy, simply navigate to the create groups under the "Groups" button. Key in multiple group names separated by comma to begin.

## Bulk add users to group
![](https://github.com/princenyeche/BOP/blob/master/img/bulk_add_users_to_groups.png)

This feature requires you upload a csv file, click the "Need help" button to see an example of the csv file format. Once ready, simply upload the file.

## Bulk add customers to organization
![](https://github.com/princenyeche/BOP/blob/master/img/add-customers.png)
To perform this operation, you will need to prepare your data file in the below format. It is crucial that you CSV file is structured in the below manner having 3 columns, so the app can perform the bulk operation. 

![](https://github.com/princenyeche/BOP/blob/master/img/customer_organization.png)
The name part isn’t used but it helps to nicely represent your customers during the file formulation. Use this delimiter `~>` for adding customers to multiple organization at the same time. Prior to submission, ensure you've set the “Customer selection” to “JSM Organization”.

## Bulk remove customers from projects
![](https://github.com/princenyeche/BOP/blob/master/img/customer_project.png)
A 3 column CSV file is required with the above structure. Once your file above is prepared, simply upload the file and set the option for customer selection to “JSM Project” prior to submission. Use this delimiter `~>` for adding customers to multiple projects.

## Bulk add organizations to projects
Performing bulk addition of organizations to specific Jira service management project involves you knowing the exact string for the organization and listing out your project keys that you need those organization added to. Create a CSV file having only two columns as shown below. Use this delimiter `~>` for adding organizations to multiple projects.
![](https://github.com/princenyeche/BOP/blob/master/img/organization_project.png)
Once you’re done with your file formulation, simply upload the file and the organizations will be added to those projects. 

## Audit log
![](https://github.com/princenyeche/BOP/blob/master/img/audit_log.png)

Keep track of everything you're doing by visiting the audit log to see what changes has been done or what failed.


# Support
* Please report any bugs or issues by raising a **[Support ticket](https://elfapp.website/support)** or if you have questions.
