# National ID Application Module

## Part 1: Online Application Form Implementation

### Web Interface Design & Accessibility
The module creates a fully functional web portal at `/national-id/apply` that serves as the primary entry point for public with its own controller.
The system captures essential public information across multiple categories with client side validation.

* Personal details (name, DOB, gender, district)  
* Contact information (phone, email)  
* Next of kin details  
* Document uploads (Support photo, LC letter)

![Purchase Request Gallery](https://i.postimg.cc/nV7Rw0Ks/application-form.png)

### Automated Tracking & Acknowledgment System
On submission of the form, the applicant is sent an acknowledgment email with his  tracking number to his email address.
* Sequential numbering: NID00001, NID00002, etc.
* Unique identifier for each application
* Immediate generation upon form submission

![Purchase Request Gallery](https://i.postimg.cc/CKgLkv4k/email-ack.png)

## Part 2: Backend Workflow Implementation
Multi-Stage Approval Architecture

The system implements a robust three-tier approval process that ensures  accountability at each level. All these processes are integrated with the integrated chatter system that captures every aspect of this approval action, creating a detailed log entry that includes the state transition, the  officer's identity, timestamp, and any additional notes or comments added during the review process.

We inherit the mail.thread integration (_inherit = ['mail.thread', 'mail.activity.mixin']) to acquire this functionality.

I also configured gmail's SMTP to send out emails to applicants.

### Stage 1: Verification Process
Responsible Group: group_verification_user
Function: Initial document and data verification
Verification Capabilities:
* Document quality assessment (Support photo present,lc photo present , support photo and lc letter quality good)
* Identity verification (name_match, address_match)
* Detailed notes logging (verification_notes)
* The system triggers an automated email notification by referencing the predefined template and dispatching it to the applicant's registered email address.

![Purchase Request Gallery](https://i.postimg.cc/WzQk0Gzt/verify-button.png)


![Purchase Request Gallery](https://i.postimg.cc/V60MvZsX/verified.png)


### Stage 2: Senior Approval
Responsible Group: group_senior_user 

Function: Management-level review and approval
#### Senior Review Process:
Reviews verification staff decisions via the chatter and can add his notes.
Can approve or reject applications
Full audit trail of decisions
The system then automatically dispatches a professional notification to the applicant, informing them that their application has successfully passed senior review and is now proceeding to the final approval stage. \


![Purchase Request Gallery](https://i.postimg.cc/25b37bp3/senior-approve-button-showing.png)

### Stage 3: Final Approval
Responsible Group: group_final_user 

Function: Executive sign-off and completion
Final Authority Features:

Ultimate approval authority.
Can create applications manually (emergency cases)
Triggers completion notifications
Marks application as ready for ID production


![Purchase Request Gallery](https://i.postimg.cc/cHcWR0LP/final-appove-button-showing.png)

## Hierarchical Group Structure
base.group_user (Internal User)
    
↓ implied_ids

group_verification_user (Verification Staff)
   
 ↓ implied_ids

group_senior_user (Senior Officers)
   
 ↓ implied_ids

group_final_user (Final Approvers)

Stage-Specific Restrictions

