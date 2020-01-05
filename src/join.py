# Keypirinha launcher (keypirinha.com)

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet
import urllib.parse
import json


class Join(kp.Plugin):
    """
    Enables interacting with the Join by Joaoapps API through Keypirinha.
    """
    SECTION_MAIN = 'main'
    SECTION_NOTIF = 'android notifications'
    API_ACCESSPOINT = 'https://joinjoaomgcd.appspot.com/_ah/api/'
    ITEM_JOIN = kp.ItemCategory.USER_BASE + 1

    def __init__(self):
        super().__init__()
        self.android_notifications = {}
        self.devices = []
        self.device_groups = []
        self.disabled_suggestions = []
        self.api_key = ''
        self.current_device_id = ''
        self.current_user_input = ''
        self.tts_language = ''
        self.icon = ''
        self.opener = None

    def on_start(self):
        self.opener = kpnet.build_urllib_opener()
        self.icon = self.load_icon('res://{}/icon.png'.format(self.package_full_name()))
        self._read_config()

    def on_catalog(self):
        catalog = []
        # Notify user of missing API key or lack of registered devices
        if not self.devices:
            if not self.api_key:
                err_label = 'Join: API key missing'
                err_short_desc = 'Please configure the plugin with your personal API key'
            else:
                err_label = 'Join: No registered devices'
                err_short_desc = 'No registered devices found. Can also be due to invalid API key in configuration file'

            catalog.append(
                self.create_item(
                    category=self.ITEM_JOIN,
                    label=err_label,
                    short_desc=err_short_desc,
                    target='error',
                    icon_handle=self.icon,
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.IGNORE,
                    loop_on_suggest=False
                )
            )
        # Produce full listings for all available devices
        if self.devices:
            for i in self.devices:
                catalog.append(
                    self.create_item(
                        category=self.ITEM_JOIN,
                        label='Join: ' + i.get('deviceName'),
                        short_desc='Select action for ' + i.get('deviceName'),
                        target='DID=' + i.get('deviceId'),
                        icon_handle=self.icon,
                        args_hint=kp.ItemArgsHint.REQUIRED,
                        hit_hint=kp.ItemHitHint.IGNORE,
                        loop_on_suggest=True
                    )
                )
        self.set_catalog(catalog)

    def _create_suggestions(self, user_input):
        """Create suggestions, excluding any actions disabled in configuration file"""
        suggestions = []

        if 'clipboard' not in self.disabled_suggestions:
            suggestions.append(self.create_item(
                category=self.ITEM_JOIN,
                label='Sync computer clipboard to device',
                short_desc="Syncs clipboard contents [text] to your device [android] " + self.current_device_id,
                target="send_clipboard",
                icon_handle=self.icon,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.NOARGS,
                loop_on_suggest=False
            ))
        if 'notification' not in self.disabled_suggestions:
            suggestions.append(self.create_item(
                category=self.ITEM_JOIN,
                label="Send notification: " + self.current_user_input,
                short_desc="Send text as notification to your device",
                target="send_notification",
                icon_handle=self.icon,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE,
                loop_on_suggest=False
            ))
        if 'download' not in self.disabled_suggestions:
            suggestions.append(self.create_item(
                category=self.ITEM_JOIN,
                label="Download: " + self.current_user_input,
                short_desc="Enter URL of file to download it directly to your device",
                target="&file=",
                icon_handle=self.icon,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE,
                loop_on_suggest=False
            ))
        if 'website' not in self.disabled_suggestions:
            suggestions.append(self.create_item(
                category=self.ITEM_JOIN,
                label="Open URL: " + self.current_user_input,
                short_desc="Enter URL of website you want to launch on your device",
                target="&url=",
                icon_handle=self.icon,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE,
                loop_on_suggest=False
            ))
        if 'find' not in self.disabled_suggestions:
            suggestions.append(self.create_item(
                category=self.ITEM_JOIN,
                label='Find device',
                short_desc="Will make your device ring loudly [Android]",
                target="&find=true",
                icon_handle=self.icon,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE,
                loop_on_suggest=False
            ))
        if 'speak' not in self.disabled_suggestions:
            suggestions.append(self.create_item(
                category=self.ITEM_JOIN,
                label="Speak: " + self.current_user_input,
                short_desc='Speak sentence on device [Android]',
                target="&say=",
                icon_handle=self.icon,
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.IGNORE,
                loop_on_suggest=False
            ))
        if 'app' not in self.disabled_suggestions:
            suggestions.append(self.create_item(
                category=self.ITEM_JOIN,
                label="Open App: " + self.current_user_input,
                short_desc="Launch an app remotely on your device [Android]",
                target="&app=",
                icon_handle=self.icon,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE,
                loop_on_suggest=False
            ))
        self.set_suggestions(suggestions)

    def on_suggest(self, user_input, items_chain):
        if not items_chain or items_chain[0].category() != self.ITEM_JOIN:
            return

        # If device is selected from catalog, store selection
        if items_chain[len(items_chain) - 1].target()[:4] == "DID=":
            self.current_device_id = items_chain[len(items_chain) - 1].target().split('=')[1]

        # Store current user input and create suggestions
        self.current_user_input = user_input
        self._create_suggestions(user_input)

    def on_execute(self, item, action):
        """Perform action related to selected item"""
        if item.category() != self.ITEM_JOIN:
            return

        item_category = item.category()
        item_label = item.label()  # use this for command (although need to get rid of user input somehow... perhaps item_label - user_input?
        item_target = item.target()  # put the actual target here, as in device id, then stored actions could still work fine!

        if item_target == "send_notification":
            self._send_notification(self.current_user_input)
        elif item_target == "send_clipboard":
            self._build_request("&clipboard=" + self._uri_encode(kpu.get_clipboard()))
        elif item_target == "&url=" or item_target == "&file=":
            if self.current_user_input[:4] != 'http':
                self.current_user_input = 'https://' + self.current_user_input
            self._build_request(item_target + self.current_user_input)
        elif item_target == "&say=":
            if self.current_user_input[0] == '!':
                say_language = self.current_user_input[1:3] # Get language code from user_input
                say_message = self.current_user_input[4:]   # Get message part from user_input
            else:
                say_language = self.tts_language
                say_message = self.current_user_input
            self._build_request('&language=' + say_language + item_target + self._uri_encode(say_message))
        elif item_target[0] == '&':
            self._build_request(item_target + self._uri_encode(self.current_user_input))

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self._read_config()
            self.on_catalog()
        if flags & kp.Events.NETOPTIONS:
            self.opener = kpnet.build_urllib_opener()

    def _read_config(self):
        self.android_notifications = {}
        self.device_groups = []
        self.disabled_suggestions = []

        settings = self.load_settings()
        self.api_key = settings.get("api_key", section=self.SECTION_MAIN, fallback='')
        self.tts_language = settings.get("tts_language", section=self.SECTION_MAIN, fallback='EN')
        self.device_groups = settings.get("device_groups", section=self.SECTION_MAIN, fallback='').split(',')
        disabled_suggestions = settings.get("disabled_actions", section=self.SECTION_MAIN, fallback='').split(',')
        for i in disabled_suggestions:
            self.disabled_suggestions.append(i.strip())
        self.android_notifications.update({'title': settings.get("title", section=self.SECTION_NOTIF, fallback=''),
                                           'icon': settings.get("icon", section=self.SECTION_NOTIF, fallback=''),
                                           'smallicon': settings.get("smallicon", section=self.SECTION_NOTIF, fallback=''),
                                           'priority': settings.get("priority", section=self.SECTION_NOTIF, fallback=''),
                                           'sound': settings.get("sound", section=self.SECTION_NOTIF, fallback='')
                                           })
        self.devices = self._get_devices()

    def _get_devices(self):
        """Uses the API key to retrieve all registered devices. Aligns with white and black-list in configuration"""
        devices = []
        response = self._build_request(None)

        try:
            for i in response.get('records'):
                devices.append(i)
            # If any groups are specified in configuration file, add them to list
            for i in self.device_groups:
                if i:
                    devices.append({'deviceId': i.strip(), 'deviceName': i.strip()})
        except (TypeError, AttributeError):
            self.err("Please register at least one device with Join")

        return devices

    def _build_request(self, message):
        """Builds and triggers transmission of API request"""
        if message:
            api_action = "messaging/v1/sendPush?"
            device_id = "&deviceId=" + self.current_device_id + "&apikey="
            api_request = self.API_ACCESSPOINT + api_action + message + device_id + self.api_key
            self._do_send(api_request)
        else:
            api_action = "registration/v1/listDevices?apikey="
            api_request = self.API_ACCESSPOINT + api_action + self.api_key
            return self._do_send(api_request)

    def _do_send(self, api_request):
        """Sends Join API request"""
        try:
            with self.opener.open(api_request) as response:
                content = json.loads(response.read().decode(response.headers.get_content_charset()))
                # Check for success and output any received error reason to console
                if not content.get("success"):
                    self.err(content.get("errorMessage"))
                return content
        except Exception as e:
            self.err("Error in transmission: ", e)

    def _send_notification(self, input_text):
        """Retrieves clipboard and parses into shareable format"""
        notification = "title=" + self._uri_encode(self.android_notifications.get('title')) + \
                       "&text=" + self._uri_encode(input_text) +\
                       "&icon=" + self.android_notifications.get('icon') +\
                       "&smallicon=" + self.android_notifications.get('smallicon') +\
                       "&priority=" + self.android_notifications.get('priority') +\
                       "&sound=" + self.android_notifications.get('sound')
        self._build_request(notification)

    def _uri_encode(self, message):
        """Returns message in URI safe encoding"""
        return urllib.parse.quote_plus(message)
