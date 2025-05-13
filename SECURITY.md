# Security Policy

Security is very important to the **BulkOps app** and its users and we're committed to responsible reporting of security-related issues. Please help to report any security issues with this app. See below for more details

## Code Scanning
We regularly scan our code for any potential security vulnerability and we check all dependencies for any impact on vulnerability before committing such changes to the release version. We use several tools to perform such scans such as **Codacy** and **Snyk.io** to monitor for any potential security vulnerability and provide mitigation measures where necessary. We regularly scan our code base to ensure best practices in writing code and mitigating any known threats relating to the use of certain code structures.

## Confidentiality
For cloud-based users, there's no interaction or storage of end-user data. Any information supplied to the app is processed immediately and discarded and no end-user data is stored. Access to log data is restricted to the [author](https://github.com/princenyeche) of the app and all that information is confidential.

## Testing
We run automated and user-based tests for any update and upgrade that is done on the app, we use apps such as **Travis-ci** to perform automated tests when updates are done. We check for vulnerabilities within dependencies to know and understand if they impact the app in any way or form. If there are impacts, we provide mitigation steps to remedy the issue.

## Disaster Recovery
For cloud-based users, daily backup of the database is done in privately encrypted servers. This database is used to store log data used in the **audit** log feature and user-provided data during sign-up. This database **does not store** any end-user data or any uploaded file data.


## Bug Bounties
We appreciate all efforts taken to keep this app safe for use and we encourage the report of such vulnerability if found. However, the **BulkOps app** is an open-source project and **does not run any bug bounty programs**


## Disclosing Security Issues
The process we've adopted to take security issues from private to public involves multiple steps.
Approximately one week before public disclosure we provide a security advisory, so it is important to watch our [repository](https://github.com/princenyeche/BOP) for those users who have local installations. For the cloud users, we'll typically perform an update automatically with the fix to the vulnerability as soon as possible once, we've detected it.

| High | Medium                 | Low |
| ------- | ------------------ |--------|
| Remote code execution    | Broken authentication | Data exposure |
| SQL injection    | Cross-site scripting (XSS) | Unvalidated redirects |
|   | Cross-site request forgery (CSRF) | |

On the day of disclosure, the following steps will be taken:
- Apply the relevant patch(es) to the *BulkOps app* code base.
- Issue the relevant release in the [BOP](https://github.com/princenyeche/BOP) git repository.
- Create a [security advisory](https://github.com/princenyeche/BOP/security/advisories) describing the issue and its resolution. We'll also credit the author (if they want to be mentioned publicly)


## Supported Versions

The below release version is supported. We encourage you to update to the latest version of **BulkOps app** if you're using a local install. For the cloud version, this is updated frequently after testing and security validation of the dependencies have been completed.

| Version | Supported          |
| ------- | ------------------ |
| v4.3.1    | :white_check_mark: |
| v4.3.0    | :white_check_mark: |
| v4.2.9    | :white_check_mark: |
| v4.2.8    | :white_check_mark: |
| v4.2.7    | :x: |
| v4.2.6    | :x: |
| v4.2.5    | :x: |
| v4.2.4    | :x: |
| v4.2.3    | :x: |
| v4.2.2    | :x: |
| v4.2.1    | :x: |
| v4.2.0    | :x: |
| v4.1.7    | :x: |
| v4.1.6    | :x: |
| v4.1.5    | :x: |
| v4.1.4    | :x: |
| v4.1.3    | :x: |
| v4.1.2    | :x: |
| v4.1.1    | :x: |
| v4.1.0    | :x: |
| v4.0.9    | :x: |
| v4.0.8    | :x: |
| v4.0.7    | :x: |
| v4.0.6    | :x: |
| v4.0.5    | :x: |
| v4.0.4    | :x: |
| v4.0.3    | :x: |
| v4.0.2    | :x: |
| v4.0.1    | :x: |
| v4.0.0    | :x: |
| v3.8.7    | :x: |
| v3.8.6    | :x: |
| v3.8.5    | :x: |
| v3.5.7    | :x: |
| v3.5.6    | :x: |
| v3.5.5    | :x: |
| v3.5.2    | :x: |
| v3.0.0    | :x: |
| v2.0.8    | :x: |
| v2.0.7    | :x: |
| v2.0.6    | :x: |
| v2.0.5    | :x: |
| v2.0.4    | :x: |
| v2.0.3    | :x: |
| v2.0.2    | :x: |
| v2.0.1    | :x: |
| v2.0.0    | :x: |
| v1.2.5    | :x: |
| v1.2.4    | :x: |
| v1.2.3    | :x: |
| v1.2.2    | :x: |
| v1.2.1    | :x: |
| v1.2    | :x: |
| v1.1    | :x: |
| v1.0    | :x: |


## Reporting A Vulnerability

For any bugs or vulnerabilities please raise a **[Support ticket](https://elfapp.website/support)**. Please try to be explicit as possible, stating all the steps taken and the reproduction of the security issue. If you believe you've found a vulnerability within **BulkOps app** that has a security impact, please send us an email to [support[at]elfapp.website](mailto:support%40elfapp.website), indicating the vulnerability and describing the problem with steps of reproduction and we request not to publicly disclose the issue until it has been addressed by us.  

### You can expect
- Once you've raised a ticket or sent an email, we will look into the issue within 48 hours and get back to you. 
- We will follow up if and when we have confirmed the issue with a timeline for a fix.
- We will create a [Github advisory](https://github.com/princenyeche/BOP/security/advisories) of the issue and publish it when a fix has been implemented and deployed within the repository.
- We will keep you informed when the fix has been applied.
