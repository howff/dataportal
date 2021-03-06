# 1.12 arb Mon  1 Apr 14:39:53 BST 2019 - implement InppschemaPlugin_validator_convert_level_from_restricted
#      fix bug, was always using resource number 0, should be read from key.
# 1.11 arb Sun 24 Mar 01:51:44 GMT 2019 - inherit package create/update to force dataset into group
# 1.10 arb Fri 22 Mar 19:16:38 GMT 2019 - convert topic_category into group
# 1.09 arb Fri 22 Mar 01:05:24 GMT 2019 - fix json quoting when converting level to restricted
# 1.08 arb Wed 20 Mar 17:22:28 GMT 2019 - convert_bbox_to_spatial handles datasets without srs
# 1.07 arb Wed Jan 23 11:18:58 GMT 2019 - added two validators to handle 'restricted' field of resource metadata
# 1.06 arb Mon Jan 21 15:50:00 GMT 2019 - added mime type for GeoJSON
# 1.05 arb Thu Jan 17 17:23:23 GMT 2019 - added level and allowed_users for restricted plugin
# 1.04 arb Thu 17 Jan 09:57:17 GMT 2019 - use inppckan_convert_bbox_to_geojson to perform the conversion.
#      Add convert_bbox_to_spatial validator to spatial field.
# 1.03 arb - create spatial extra
# 1.02 arb Tue 23 Oct 18:08:18 BST 2018 - added metadata, added logging, removed unused class.
# 1.01 arb Mon  3 Sep 17:31:01 BST 2018 - added INPP metadata functions but not implemented the actual schema yet.

# This plugin extends the default CKAN schema with new metadata fields.
# It also contains code to update the 'spatial' metadata with a
# GeoJSON value that is calculated from the N,S,W,E extents entered.
# It also extends the default CKAN schema for resources to add the
# fields required by the 'restricted' plugin allowing for resources
# to be restricted to certain users.

# XXX TODO
# Modify show_package_schema to change values to "Hidden" if protected and not sysadmin.
# Better to do it here rather than in the HTML template.

# See the documentation:
# http://docs.ckan.org/en/2.8/extensions/adding-custom-fields.html
# The convert_to/from_extras code is here:
# /usr/lib/ckan/default/src/ckan/ckan/logic/converters.py
# Adding resource metadata:
# https://docs.ckan.org/en/2.8/extensions/adding-custom-fields.html#adding-custom-fields-to-resources
# For adding a mime type:
# https://docs.ckan.org/en/2.8/maintaining/filestore.html#filestore-api
# GeoJSON mimetype: https://tools.ietf.org/html/rfc7946

# ckan plugin
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.plugins.toolkit import Invalid
# to patch the package_create/update methods
import ckan.logic
from ckan.logic.action.create import package_create
from ckan.logic.action.update import package_update
# general
import json
import logging
import mimetypes
import inppckan

# Doesn't work (is ignored): logging.basicConfig(filename="/tmp/ckan_debug.log", level=logging.DEBUG) # XXX arb ???
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Our validator converts the bounding box values into a spatial extra
# It takes the values from inpp_north/south/east/west and creates a
# GeoJSON string which is placed into the extra called 'spatial'.
# 1 param (value) return value, or it can be converted if you wish
# 2 param (value, context) likewise. nb can raise(Invalid) if you wish.
# 4 param (key, flattened_data, errors, context) return None as it can
#  update stuff
# See https://docs.ckan.org/en/2.8/extensions/adding-custom-fields.html#custom-validators

# flattened_data for a dataset may look like this:
#   ('extras', 27, 'key'): 'inpp_west_longitude',
#   ('inpp_west_longitude',): u'-11',
# the resources of the dataset are like this:
# eg. to get the id of the first (0) resource:
#   ('resources', 0, 'id'): u'b96f04cb-00ab-48aa-8f85-4243e29ffa73',
# the extras are like this:
#   ('__extras',): {
#     'num_resources': 1,
#     'metadata_modified': '2019-01-23T12:59:53.892922',
#      organization': { 'title':'My Organisation' }
#   }

def InppschemaPlugin_validator_convert_bbox_to_spatial(key, flattened_data, errors, context):
    log.debug("InppschemaPlugin convert_bbox_to_spatial")
    log.debug("InppschemaPlugin flattened_data is %s" % (str(flattened_data)))

    # Lookup the entered values (warning: might not be validated/converted yet)
    # in case we are given a dataset without our values we return empty
    try:
        srs = flattened_data[('inpp_spatial_reference_system',)]
        n = flattened_data[('inpp_north_latitude',)]
        s = flattened_data[('inpp_south_latitude',)]
        w = flattened_data[('inpp_west_longitude',)]
        e = flattened_data[('inpp_east_longitude',)]
    except:
        srs = n = s = w = e = ''

    # Construct GeoJSON format from bounding box
    # eg. '{ "type": "Polygon", "coordinates": [[ [ -59.26,-51.94 ], [ -57.62,-51.94 ], [ -57.62,-51.16 ], [ -59.26,-51.16 ], [ -59.26,-51.94 ] ]] }'
    geojson = inppckan.inppckan_convert_bbox_to_geojson(srs, n, s, w, e)

    log.debug("InppschemaPlugin SRS %s" % (srs))
    log.debug("InppschemaPlugin N %s" % (n))
    log.debug("InppschemaPlugin S %s" % (s))
    log.debug("InppschemaPlugin W %s" % (w))
    log.debug("InppschemaPlugin E %s" % (e))
    log.debug("InppschemaPlugin GeoJSON %s" % (geojson))

    # check if spatial exists first
    # what to do if it does?
    if ('spatial',) in flattened_data:
        log.debug("InppschemaPlugin existing spatial (will be overwritten) was %s" % (flattened_data[('spatial',)]))

    # Give the spatial extra the new GeoJSON value.
    flattened_data[('spatial',)] = geojson


def InppschemaPlugin_validator_convert_level_to_restricted(key, flattened_data, errors, context):
    log.debug("InppschemaPlugin_validator_convert_level_to_restricted flattened_data is %s" % (str(flattened_data)))
    log.debug("InppschemaPlugin_validator_convert_level_to_restricted key is %s" % (str(key)))
    log.debug("InppschemaPlugin_validator_convert_level_to_restricted key resource num is %s" % key[1])
    log.debug("InppschemaPlugin_validator_convert_level_to_restricted key value is %s" % flattened_data[key])
    log.debug("InppschemaPlugin_validator_convert_level_to_restricted context is %s" % (str(context)))

    # called with a key like ('resource', N, 'level') we need the value of N to determine which resource to update
    resource_num = key[1]

    if not ('resources', resource_num, 'level') in flattened_data or not ('resources', resource_num, 'allowed_users') in flattened_data:
        return
    lv = flattened_data[('resources', resource_num, 'level')]
    au = flattened_data[('resources', resource_num, 'allowed_users')]
    #rr = flattened_data[('restricted',)]
    #log.debug("XXX level is %s" % lv)
    #log.debug("XXX restricted is %s" % rr)
    #log.debug("XXX level is %s" % lv)
    #log.debug("XXX users is %s" % au)
    # WRONG json = '{\"allowed_users\": \"%s\", \"level\": \"%s\"}' % (au, lv)
    restricted_json = '{"allowed_users": "%s", "level": "%s"}' % (au, lv)
    log.debug("InppschemaPlugin_validator_convert_level_to_restricted setting ('resources',%d,'restricted') to %s" % (resource_num, restricted_json))
    flattened_data[('resources', resource_num, 'restricted')] = restricted_json


def InppschemaPlugin_validator_convert_level_from_restricted(key, flattened_data, errors, context):
    log.debug("InppschemaPlugin_validator_convert_level_from_restricted flattened_data is %s" % (str(flattened_data)))
    log.debug("InppschemaPlugin_validator_convert_level_from_restricted key is %s" % (str(key)))
    log.debug("InppschemaPlugin_validator_convert_level_from_restricted key resource num is %s" % key[1])
    log.debug("InppschemaPlugin_validator_convert_level_from_restricted key value is %s" % flattened_data[key])

    # called with a key like ('resource', N, 'level') we need the value of N to determine which resource to update
    resource_num = key[1]

    # Would we ever want to populate the level fields from the restricted field?
    # The latter is never modified directly. Except when a script does it? XXX
    if not ('resources', resource_num, 'restricted') in flattened_data:
        return
    restricted_json = flattened_data[('resources', resource_num, 'restricted')]
    restricted_dict = json.loads(restricted_json)
    flattened_data[('resources', resource_num, 'level')] = restricted_dict['level']
    flattened_data[('resources', resource_num, 'allowed_users')] = restricted_dict['allowed_users']
    log.debug("InppschemaPlugin_validator_convert_level_from_restricted setting level %s allowed_users %s" % (flattened_data[('resources', resource_num, 'level')], flattened_data[('resources', resource_num, 'allowed_users')]))


def InppschemaPlugin_validator_convert_topic_category_to_group(key, flattened_data, errors, context):
    return
    # XXX the rest of this code no longer used because it is not effective
    # the replacement is to extend the package_create and package_update methods instead, see below.
    log.debug("InppschemaPlugin_validator_convert_topic_category_to_group NotYetImplemented flattened_data is %s" % (str(flattened_data)))
    # First look up the group which matches the given topic_category
    # Find its 'id' (and 'name'?)
    topic_category = flattened_data[('inpp_topic_category',)]
    topic_group = inppckan.inppckan_map_topic_category_to_group(context, topic_category)
    topic_group_id = topic_group['id']
    log.debug("InppschemaPlugin_validator_convert_topic_category_to_group XXX topic %s -> group id %s" % (topic_category, topic_group_id))
    # Need to iterate through all items in the flattened_data "list"
    # looking for tuples ('group', N, 'id')
    # If present then do nothing
    # If not present then add ('group', N+1, 'id') = topic_group_id
    # or call the action package_patch to do the same
    # XXX *** NOTE: a validator is NOT the place to be adding data!!!
    # adding a group to flattened_data does make the dataset part of that group.
    # The code below is pointless.
    already_in_group = False
    already_in_num_groups = -1
    for data_tuple in flattened_data:
        # tuple is ('group', N, 'key') so find the maximum N
        if (data_tuple[0] == 'group'):
            already_in_num_groups = max(already_in_num_groups, data_tuple[1])
            log.error("XXX Found %d groups in flattened_data" % already_in_num_groups)
        if (data_tuple[0] == 'group' and data_tuple[2] == 'id'):
            already_in_group_id = flattened_data[data_tuple]
            log.error("XXX for topic_category %s group id %s already in group id %s" % (topic_category, topic_group_id, already_in_group_id))
            already_in_group = True
    if already_in_group:
        log.error("XXX already in group")
    else:
        already_in_num_groups += 1
        log.error("XXX need to add to group id %s" % topic_group_id)
        log.error("XXX will be group number %d for this dataset", already_in_num_groups)
        for topic_group_elem in topic_group:
            log.error("XXX add %s = %s" % (topic_group_elem, topic_group[topic_group_elem]))
            flattened_data[('group', already_in_num_groups, topic_group_elem)] = topic_group[topic_group_elem]
        #flattened_data[('group', already_in_num_groups, 'id')] = topic_group_id
        #log.error("XXX flattened_data has %s" % flattened_data[('group', already_in_num_groups, 'id')] )
    log.error("ZZZ done")

# ---------------------------------------------------------------------
# Functions to extend the behaviour of the package_create and package_update methods
# to map from inpp_topic_category into the ckan group so when the user selects a
# particular topic category it forces the package to become a member of that group.

def InppschemaPlugin_add_group_to_package_based_on_topic_category(context, data_dict):
    # Lookup the topic category in the CSV file
    if not 'inpp_topic_category' in data_dict:
        return data_dict
    log.error("InppschemaPlugin_add_group_to_package_based_on_topic_category")
    topic_category = data_dict['inpp_topic_category']
    topic_group = inppckan.inppckan_map_topic_category_to_group(context, topic_category)
    if topic_group is None:
        return data_dict
    if 'id' in topic_group:
        topic_group_id = topic_group['id']
    else:
        return data_dict
    # Add or replace the groups dict with { 'id' : the id of the matching group }
    if 'groups' in data_dict:
        data_dict['groups'].append({'id':topic_group_id})
    else:
        data_dict['groups'] = [{'id':topic_group_id}]
    return data_dict

def InppschemaPlugin_package_create(context, data_dict):
    data_dict = InppschemaPlugin_add_group_to_package_based_on_topic_category(context, data_dict)
    return package_create(context, data_dict)

def InppschemaPlugin_package_update(context, data_dict):
    data_dict = InppschemaPlugin_add_group_to_package_based_on_topic_category(context, data_dict)
    return package_update(context, data_dict)

# ---------------------------------------------------------------------
# Our class contains the additional schema elements required for our metadata

class InppschemaPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IValidators) # for get_validators function
    #plugins.implements(plugins.ITemplateHelpers) # for get_helpers function

    log.debug("InppschemaPlugin created")

    # IActions
    # Extend the package_create/update methods
    def get_actions(self):
        return {'package_create': InppschemaPlugin_package_create,
            'package_update': InppschemaPlugin_package_update }

    # Return the list of validators which we supply (functions must be global)
    def get_validators(self):
        log.debug("InppschemaPlugin get_validators returning 3 incl bbox and level")
        return { 'convert_bbox_to_spatial':  InppschemaPlugin_validator_convert_bbox_to_spatial,
            'convert_topic_category_to_group':   InppschemaPlugin_validator_convert_topic_category_to_group,
            'convert_level_to_restricted':   InppschemaPlugin_validator_convert_level_to_restricted,
            'convert_level_from_restricted': InppschemaPlugin_validator_convert_level_from_restricted }


    # Helper function to prevent duplicated code
    # Caller from create_package_schema and update_package_schema.
    def _modify_package_schema(self, schema):
        log.debug("InppschemaPlugin _modify_package_schema called")

        schema.update({
            # INPPSCHEMA_UPDATE_START
            'inpp_region': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_language': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_topic_category': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_temporal_extent_start': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_temporal_extent_end': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_dataset_reference_date': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_lineage': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_west_longitude': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_south_latitude': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_east_longitude': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_north_latitude': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_spatial_reference_system': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_responsible_organisation_name': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_contact_mail_address': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_responsible_party_role': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_access_limitations': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_use_constraints': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_data_format': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_update_frequency': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_accuracy': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_resource_type': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_original_title': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_metadata_date': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_metadata_point_of_contact': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_contact_consent': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_unique_resource_id': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            ,'inpp_research_permit_application_id': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
            # INPPSCHEMA_UPDATE_END
        })
        # Add two fields to the resource schema for the restricted plugin
        log.debug("InppschemaPlugin _modify_package_schema adding restricted to resources schema")
        schema['resources'].update({
            'level': [ toolkit.get_validator('ignore_missing'), toolkit.get_validator('convert_level_to_restricted') ]
            ,'allowed_users': [ toolkit.get_validator('ignore_missing') ]
            ,'restricted': [ toolkit.get_validator('ignore_missing') ]
        })
        # If the schema doesn't already have a 'spatial' extra then add it now
        if not 'spatial' in schema:
            log.debug("InppschemaPlugin _modify_package_schema adding spatial to schema")
            schema.update({'spatial': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_bbox_to_spatial'),
                                 toolkit.get_converter('convert_to_extras')]})
        return schema

    # The create_package_schema() function is used whenever a new dataset
    # is created, we want to update the default schema and insert our
    # custom field here. We will fetch the default schema defined in
    # default_create_package_schema() by running
    # create_package_schema()'s super function and update it.

    def create_package_schema(self):
        log.debug("InppschemaPlugin create_package_schema called")
        # get the default schema in our plugin
        schema = super(InppschemaPlugin, self).create_package_schema()
        # add our custom fields
        schema = self._modify_package_schema(schema)
        return schema

    # The CKAN schema is a dictionary where the key is the name of the field
    # and the value is a list of validators and converters.
    # Here we have a validator to tell CKAN to not raise a validation error
    # if the value is missing and a converter to convert the value to and save
    # as an extra. We will want to change the update_package_schema() function
    # with the same update code.

    def update_package_schema(self):
        log.debug("InppschemaPlugin update_package_schema called")
        schema = super(InppschemaPlugin, self).update_package_schema()
        # add our custom fields
        schema = self._modify_package_schema(schema)
        return schema

    # The show_package_schema() is used when the package_show() action is called
    # We want the default_show_package_schema to be updated to include our
    # custom fields. This time, instead of converting to an extras field,
    # we want our field to be converted from an extras field.
    # So we want to use the convert_from_extras() converter.

    def show_package_schema(self):
        log.debug("InppschemaPlugin show_package_schema called")
        schema = super(InppschemaPlugin, self).show_package_schema()
        #log.debug("InppschemaPlugin schema before = {}".format(str(schema)))
        schema.update({
            # INPPSCHEMA_SHOW_START
            'inpp_region': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_language': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_topic_category': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_temporal_extent_start': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_temporal_extent_end': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_dataset_reference_date': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_lineage': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_west_longitude': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_south_latitude': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_east_longitude': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_north_latitude': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_spatial_reference_system': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_responsible_organisation_name': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_contact_mail_address': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_responsible_party_role': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_access_limitations': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_use_constraints': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_data_format': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_update_frequency': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_accuracy': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_resource_type': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_original_title': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_metadata_date': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_metadata_point_of_contact': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_contact_consent': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_unique_resource_id': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            ,'inpp_research_permit_application_id': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
            # INPPSCHEMA_SHOW_END
        })
        # Add two fields to the resource schema for the restricted plugin
        # XXX no use of convert_from_restricted at this stage
        log.debug("InppschemaPlugin show_package_schema adding restricted to resources schema")
        schema['resources'].update({
            'level': [ toolkit.get_validator('ignore_missing') ]
            ,'allowed_users': [ toolkit.get_validator('ignore_missing') ]
            ,'restricted': [ toolkit.get_validator('convert_level_from_restricted'), toolkit.get_validator('ignore_missing') ]
        })
        # If the schema doesn't already have a 'spatial' extra then add it now
        if not 'spatial' in schema:
            log.debug("InppschemaPlugin show_package_schema adding spatial to schema")
            schema.update({'spatial': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('convert_bbox_to_spatial'), # XXX should this be here???
                            toolkit.get_validator('ignore_missing')]})
        return schema

    # The package_types() function defines a list of dataset types that this
    # plugin handles. Each dataset has a field containing its type.
    # Plugins can register to handle specific types of dataset and ignore others.
    # Since our plugin is not for any specific type of dataset and we want our
    # plugin to be the default handler, we update the plugin code to contain:

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    # In order for our new field to be visible on the CKAN front-end, we need to
    # update the templates.
    # Make the plugin implement the IConfigurer interface.
    # This interface allows to implement a function update_config() that
    # allows us to update the CKAN config, in our case we want to add an
    # additional location for CKAN to look for templates:

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('fanstatic', 'inppschema')
        mimetypes.add_type('application/geo+json', '.geojson') # As per RFC, not application/json
        log.debug("InppschemaPlugin update_config called")


# Test
if __name__ == "__main__":
    serickan.inppckan_map_topic_category_to_group('test')
