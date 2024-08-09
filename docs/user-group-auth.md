# User Groups and Authorization Details

## Introduction
This document outlines the user groups and their associated permissions within the system. It provides an overview of each group's role and the specific actions they are authorized to perform, based on the provided information.

## Groups

The system defines six distinct user groups:

1. ADMIN
2. DIRECTORS_OFFICE
3. GUEST
4. MONITORING_EXPERT
5. REGIONAL_COORDINATOR
6. REPORTING_TEAM

Each group has a specific set of permissions tailored to their role in the organization.

## Permissions

### Admin
The Admin group has the highest level of access and control within the system. They can perform all operations across various modules including user management, content creation, and system configuration.

**Key Permissions:**
- Full control over user accounts and portfolios
- Management of all types of content (communications, contacts, updates, crises, entries, figures, events, etc.)
- Configuration of system-wide settings (e.g., organization kinds, GIDD release metadata)
- Approval and sign-off capabilities for critical actions (e.g., approving reports, updating GIDD data)

### Directors Office
The Directors Office group has limited permissions, focused on report management.

**Key Permissions:**
- Can change reports

### Guest
The Guest group currently has no specified permissions in the system.

### Monitoring Expert
The Monitoring Expert group has broad permissions related to data entry, content management, and reporting.

**Key Permissions:**
- Management of communications, contacts, and contextual updates
- Creation and modification of entries, figures, and reports
- Organization management
- Ability to approve figures and reports
- Crisis management
- Event management (including assigning and removing event levels)

### Regional Coordinator
The Regional Coordinator group has extensive permissions similar to the Monitoring Expert, with additional capabilities related to event management and sign-off procedures.

**Key Permissions:**
- All permissions of the Monitoring Expert
- Management of actors and contexts of violence
- Ability to sign off on events and reports
- Can update public figure visibility in GIDD (Global Internal Displacement Database)
- Management of organization kinds

### Reporting Team
The Reporting Team group has focused permissions related to report creation and organization management.

**Key Permissions:**
- Creation and management of reports
- Addition and modification of figure tags
- Organization management

## Modules and Content Types

The system includes various modules and content types that users interact with, depending on their permissions:

1. Contact: Communications and contact management
2. Contextual Update: Managing contextual information
3. Country: Contextual analysis and summaries
4. Crisis: Crisis information management
5. Entry: Entries and figures management
6. Event: Managing events, actors, and contexts of violence
7. Organization: Organization and organization kind management
8. Parking Lot: Managing parked items
9. Report: Report creation, management, and commenting
10. Resource: Resource management
11. Review: Review commenting
12. GIDD: Global Internal Displacement Database management

## Permission Types

The system uses a granular permission system, with the following types of permissions:

- Can add
- Can change
- Can delete
- Can approve/unapprove
- Can assign
- Can clear
- Can sign-off
- Can update

These permission types are applied to various content types and actions within the system, allowing for fine-grained access control.

This document provides an overview of the current user groups and permissions structure based on the available information. It serves as a reference for understanding the role-based access control implemented in the system.

## Detailed Permissions

### Admin

- contact | communication | Can add communication
- contact | communication | Can change communication
- contact | communication | Can delete communication
- contact | contact | Can add contact
- contact | contact | Can change contact
- contact | contact | Can delete contact
- contextualupdate | contextual update | Can add contextual update
- contextualupdate | contextual update | Can change contextual update
- contextualupdate | contextual update | Can delete contextual update
- contrib | client | Can add client
- contrib | client | Can change client
- contrib | client | Can delete client
- country | contextual analysis | Can add contextual analysis
- country | contextual analysis | Can change contextual analysis
- country | contextual analysis | Can delete contextual analysis
- country | summary | Can add summary
- country | summary | Can change summary
- country | summary | Can delete summary
- crisis | crisis | Can add crisis
- crisis | crisis | Can change crisis
- crisis | crisis | Can delete crisis
- entry | entry | Can add entry
- entry | entry | Can change entry
- entry | entry | Can delete entry
- entry | figure | Can add figure
- entry | figure | Can approve/unapprove figure
- entry | figure | Can change figure
- entry | figure | Can delete figure
- entry | figure tag | Can add figure tag
- entry | figure tag | Can change figure tag
- entry | figure tag | Can delete figure tag
- event | actor | Can add actor
- event | actor | Can change actor
- event | actor | Can delete actor
- event | context of violence | Can add context of violence
- event | context of violence | Can change context of violence
- event | context of violence | Can delete context of violence
- event | event | Can add event
- event | event | Can assign an event level
- event | event | Can change event
- event | event | Can clear any assignee from event
- event | event | Can clear self assigned event
- event | event | Can delete event
- event | event | Can remove an event level
- event | event | Can sign-off event
- gidd | release metadata | Can update release meta data
- gidd | status log | Can update GIDD data
- organization | organization | Can add organization
- organization | organization | Can change organization
- organization | organization | Can delete organization
- organization | organization kind | Can add organization kind
- organization | organization kind | Can change organization kind
- organization | organization kind | Can delete organization kind
- parking_lot | parked item | Can add parked item
- parking_lot | parked item | Can change parked item
- parking_lot | parked item | Can delete parked item
- report | report | Can add report
- report | report | Can approve the report
- report | report | Can change report
- report | report | Can delete report
- report | report | Can sign off the report
- report | report | Can update public figure visibility in GIDD
- report | report comment | Can add report comment
- report | report comment | Can change report comment
- report | report comment | Can delete report comment
- resource | resource | Can add resource
- resource | resource | Can change resource
- resource | resource | Can delete resource
- review | review comment | Can add review comment
- review | review comment | Can change review comment
- review | review comment | Can delete review comment
- users | portfolio | Can add portfolio
- users | portfolio | Can change portfolio
- users | portfolio | Can delete portfolio
- users | user | Can add user
- users | user | Can change user
- users | user | Can delete user

### Directors Office

- report | report | Can change report

### Guest

N/A

### Monitoring Expert

- contact | communication | Can add communication
- contact | communication | Can change communication
- contact | communication | Can delete communication
- contact | contact | Can add contact
- contact | contact | Can change contact
- contact | contact | Can delete contact
- contextualupdate | contextual update | Can add contextual update
- contextualupdate | contextual update | Can change contextual update
- contextualupdate | contextual update | Can delete contextual update
- country | contextual analysis | Can add contextual analysis
- country | contextual analysis | Can change contextual analysis
- country | contextual analysis | Can delete contextual analysis
- country | summary | Can add summary
- country | summary | Can change summary
- country | summary | Can delete summary
- crisis | crisis | Can add crisis
- crisis | crisis | Can change crisis
- crisis | crisis | Can delete crisis
- entry | entry | Can add entry
- entry | entry | Can change entry
- entry | entry | Can delete entry
- entry | figure | Can add figure
- entry | figure | Can approve/unapprove figure
- entry | figure | Can change figure
- entry | figure | Can delete figure
- entry | figure tag | Can add figure tag
- entry | figure tag | Can change figure tag
- entry | figure tag | Can delete figure tag
- event | event | Can add event
- event | event | Can assign an event level
- event | event | Can change event
- event | event | Can clear any assignee from event
- event | event | Can clear self assigned event
- event | event | Can delete event
- event | event | Can remove an event level
- organization | organization | Can add organization
- organization | organization | Can change organization
- organization | organization | Can delete organization
- parking_lot | parked item | Can add parked item
- parking_lot | parked item | Can change parked item
- parking_lot | parked item | Can delete parked item
- report | report | Can add report
- report | report | Can approve the report
- report | report | Can change report
- report | report | Can delete report
- report | report comment | Can add report comment
- report | report comment | Can change report comment
- report | report comment | Can delete report comment
- resource | resource | Can add resource
- resource | resource | Can change resource
- resource | resource | Can delete resource
- review | review comment | Can add review comment
- review | review comment | Can change review comment
- REGIONAL_COORDINATOR
- contact | communication | Can add communication
- contact | communication | Can change communication
- contact | communication | Can delete communication
- contact | contact | Can add contact
- contact | contact | Can change contact
- contact | contact | Can delete contact
- contextualupdate | contextual update | Can add contextual update
- contextualupdate | contextual update | Can change contextual update
- contextualupdate | contextual update | Can delete contextual update
- country | contextual analysis | Can add contextual analysis
- country | contextual analysis | Can change contextual analysis
- country | contextual analysis | Can delete contextual analysis
- country | summary | Can add summary
- country | summary | Can change summary
- country | summary | Can delete summary
- crisis | crisis | Can add crisis
- crisis | crisis | Can change crisis
- crisis | crisis | Can delete crisis
- entry | entry | Can add entry
- entry | entry | Can change entry
- entry | entry | Can delete entry
- entry | figure | Can add figure
- entry | figure | Can approve/unapprove figure
- entry | figure | Can change figure
- entry | figure | Can delete figure
- entry | figure tag | Can add figure tag
- entry | figure tag | Can change figure tag
- entry | figure tag | Can delete figure tag
- event | actor | Can add actor
- event | actor | Can change actor
- event | actor | Can delete actor
- event | context of violence | Can add context of violence
- event | context of violence | Can change context of violence
- event | context of violence | Can delete context of violence
- event | event | Can add event
- event | event | Can assign an event level
- event | event | Can change event
- event | event | Can clear any assignee from event
- event | event | Can clear self assigned event
- event | event | Can delete event
- event | event | Can remove an event level
- event | event | Can sign-off event
- organization | organization | Can add organization
- organization | organization | Can change organization
- organization | organization | Can delete organization
- organization | organization kind | Can add organization kind
- organization | organization kind | Can change organization kind
- organization | organization kind | Can delete organization kind
- parking_lot | parked item | Can add parked item
- parking_lot | parked item | Can change parked item
- parking_lot | parked item | Can delete parked item
- report | report | Can add report
- report | report | Can approve the report
- report | report | Can change report
- report | report | Can delete report
- report | report | Can sign off the report
- report | report | Can update public figure visibility in GIDD
- report | report comment | Can add report comment
- report | report comment | Can change report comment
- report | report comment | Can delete report comment
- resource | resource | Can add resource
- resource | resource | Can change resource
- resource | resource | Can delete resource
- review | review comment | Can add review comment
- review | review comment | Can change review comment
- review | review comment | Can delete review comment

### Reporting Team

- entry | figure tag | Can add figure tag
- entry | figure tag | Can change figure tag
- organization | organization | Can add organization
- organization | organization | Can change organization
- report | report | Can add report
- report | report | Can change report
- report | report | Can delete report