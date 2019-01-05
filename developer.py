"""
Support to check for pull requests related to current configuration.

Configuration:

developer:
  github_personal_token: 3456784235482398577563485739

get your token from https://github.com/settings/tokens
"""
import logging
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, CONF_ICON, CONF_NAME, CONF_MODE,
    STATE_UNAVAILABLE)
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers import event
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['PyGithub']

DOMAIN = 'developer'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

HOMEASSITANT_ORGANIZATION = 'home-assistant'
HOMEASSITANT_REPO = 'home-assistant'

ATTR_LAST_UPDATED = 'last_updated'

NOTIFICATION_ID = 'developer_notification'

FRIENDLY_NAME = 'Last reviewed PR'
ENTITY_ID = 'developer.last_signaled_pr'

CONF_GITHUB_PERSONAL_TOKEN = 'github_personal_token'

CONFIG_SCHEMA = vol.Schema({DOMAIN: {
    vol.Optional(CONF_GITHUB_PERSONAL_TOKEN, default=None): cv.string,
}}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up an input slider."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    await component.async_add_entities(
        [HADeveloperEntity(config[DOMAIN].get(CONF_GITHUB_PERSONAL_TOKEN))])
    return True


class HADeveloperEntity(RestoreEntity):
    """Representation of a Home Assistant Developer."""

    def __init__(self, github_personal_token):
        """Initialize an input number."""
        self.entity_id = ENTITY_ID
        self._state = STATE_UNAVAILABLE
        self.github_personal_token = github_personal_token

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return the name of the repository."""
        return FRIENDLY_NAME 

    @property
    def state(self):
        """Return the state of the component."""
        return self._state

    @callback
    def check_new_pullrequests(self, now):
        """Check on github for pull requests on platforms currently running."""
        from github import Github
        from github.GithubException import RateLimitExceededException
        _LOGGER.debug("check_new_pullrequests")

        print(self.github_personal_token)
        github_client = Github(self.github_personal_token)
        try:
            organization = github_client.get_organization(HOMEASSITANT_ORGANIZATION)
            repository = organization.get_repo(HOMEASSITANT_REPO)
        except RateLimitExceededException as err:
            _LOGGER.error(err)
            return

        last_signaled_pr = self._state 
        _LOGGER.debug("Last signaled PR: %s", last_signaled_pr)

        installed_platforms = [p.split('.')[1] for p in list(self.hass.config.components) if "." in p]
        installed_platforms = set([p for p in installed_platforms if p not in ['homeassistant']])
        _LOGGER.debug(installed_platforms)

        pr_list = []
        for pull_request in repository.get_pulls():
            found = False
            _LOGGER.debug(pull_request.number)
            pr_list.append(pull_request.number)
            if last_signaled_pr != STATE_UNAVAILABLE and\
                pull_request.number <= int(last_signaled_pr):
                break

            for changed_file in pull_request.get_files():
                if found:
                    break
                for platform in installed_platforms:
                    if not found and\
                        platform in changed_file.filename.split('/')[-1]:
                        _LOGGER.debug("FOUND an interesting PR %s",
                                      pull_request.number)
                        self.hass.components.persistent_notification.create(
                            '&#35;{}: {}<br />'
                            '{}<br />'
                            'You are using {}'
                            ''.format(pull_request.number, pull_request.title,
                                      pull_request.html_url, platform),
                            title="New Pull Request",
                            notification_id="{}{}".format(NOTIFICATION_ID,
                                                          pull_request.number))
                        found = True

        _LOGGER.debug("Set %s to %s", self.name, max(pr_list))
        self._state = max(pr_list)

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._state = state.state

        _dt = dt_util.utcnow() + timedelta(seconds=10)
        event.async_track_utc_time_change(
            self.hass, self.check_new_pullrequests,
            hour=_dt.hour, minute=_dt.minute, second=_dt.second)
