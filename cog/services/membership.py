"""
Service module to manage membership of users in groups.
All methods return a string code that summarizes the result of the invocation.
Currently the underlying membership model includes only users and groups, no roles.
Note that the service methods do NOT include the notification functionality, which is left in the view layer.
This is because notification messages may include link to web pages (which are built from the request object),
and reference projects, as opposed to groups.
"""
from django.contrib.auth.models import User, Group, Permission
from cog.models import MembershipRequest
from django.core.urlresolvers import reverse

# return codes
RESULT_SUCCESS = 'SUCCESS'
RESULT_DUPLICATE = 'DUPLICATE'
RESULT_NOT_FOUND = 'NOT FOUND'

# Method to request membership of a user in a group (with no role specification)
# Returns the status of the request: REQUESTED, DUPLICATE, REJECTED etc.
def requestMembership(user, group):
    
    try:
        gr = MembershipRequest.objects.get(user=user, group=group)
        return RESULT_DUPLICATE
    except MembershipRequest.DoesNotExist:
        gr = MembershipRequest(user=user, group=group)
        gr.save()
        return RESULT_SUCCESS
    
# Method to cancel a membership request
def cancelMembershipRequest(user, group):
    # remove the entry from the unprocessed membership list
    mrlist = MembershipRequest.objects.filter(group=group).filter(user=user)
    if len(mrlist)>0:
        for mr in mrlist:
            mr.delete()
        
# Method to enroll a user in a group (with no role specification)
def addMembership(user, group):
    if not group in user.groups.all():
        user.groups.add(group)
        print "Enrolled user=%s in group=%s" % (user.username, group.name)
        cancelMembershipRequest(user, group)
        
        return RESULT_SUCCESS
    else:
        print "User=%s is already enrolled in group=%s" % (user.username, group.name)
        cancelMembershipRequest(user, group)
        return RESULT_DUPLICATE

# Method to disenroll a user from a group
def cancelMembership(user, group):
    
    # cancel request
    cancelMembershipRequest(user, group)
    
    if group in user.groups.all():
        user.groups.remove(group)
        print "Removed user=%s from group=%s" % (user.username, group.name)
        return RESULT_SUCCESS
    else:
        print "User=%s not found in group=%s" % (user.username, group.name)
        return RESULT_NOT_FOUND