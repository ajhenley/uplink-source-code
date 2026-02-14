/**
 * Remote computer screen renderer.
 * Receives screen data from the server via GameState events and
 * delegates rendering to the appropriate screen-type renderer.
 */
const RemoteScreen = {
    panel: null,
    panelBody: null,

    init() {
        this.panelBody = Panels.create('remote', 'REMOTE ACCESS', 600, 450);

        GameState.on('screen_updated', () => this.render());
        GameState.on('connection_updated', () => {
            if (!GameState.connection.isConnected) {
                Panels.hide('remote');
            }
        });

        Panels.hide('remote');
    },

    /**
     * Render the current remote screen based on screen type.
     */
    render() {
        const screen = GameState.currentScreen;
        if (!screen) {
            Panels.hide('remote');
            return;
        }

        Panels.show('remote');

        // Update panel title to show target IP
        const header = document.querySelector('#panel-remote .panel-title');
        if (header) {
            header.textContent = 'REMOTE: ' + (GameState.connection.targetIp || '');
        }

        // Screen type to renderer mapping (values match SCREEN_* constants in constants.py)
        const renderers = {
            1:  typeof ScreenMessage !== 'undefined' ? ScreenMessage : null,        // SCREEN_MESSAGESCREEN
            2:  typeof ScreenPassword !== 'undefined' ? ScreenPassword : null,      // SCREEN_PASSWORDSCREEN
            3:  typeof ScreenMenu !== 'undefined' ? ScreenMenu : null,              // SCREEN_MENUSCREEN
            4:  typeof ScreenBBS !== 'undefined' ? ScreenBBS : null,                // SCREEN_BBSSCREEN
            6:  typeof ScreenFileServer !== 'undefined' ? ScreenFileServer : null,  // SCREEN_FILESERVERSCREEN
            7:  typeof ScreenLinks !== 'undefined' ? ScreenLinks : null,            // SCREEN_LINKSSCREEN
            8:  typeof ScreenLog !== 'undefined' ? ScreenLog : null,                // SCREEN_LOGSCREEN
            9:  typeof ScreenSWSales !== 'undefined' ? ScreenSWSales : null,        // SCREEN_SWSALESSCREEN
            10: typeof ScreenHWSales !== 'undefined' ? ScreenHWSales : null,        // SCREEN_HWSALESSCREEN
            11: typeof ScreenRecord !== 'undefined' ? ScreenRecord : null,          // SCREEN_RECORDSCREEN
            12: typeof ScreenUserID !== 'undefined' ? ScreenUserID : null,          // SCREEN_USERIDSCREEN
            13: typeof ScreenAccount !== 'undefined' ? ScreenAccount : null,        // SCREEN_ACCOUNTSCREEN
            14: typeof ScreenContact !== 'undefined' ? ScreenContact : null,        // SCREEN_CONTACTSCREEN
            15: typeof ScreenNews !== 'undefined' ? ScreenNews : null,              // SCREEN_NEWSSCREEN
            16: typeof ScreenCriminal !== 'undefined' ? ScreenCriminal : null,      // SCREEN_CRIMINALSCREEN
            17: typeof ScreenSecurity !== 'undefined' ? ScreenSecurity : null,      // SCREEN_SECURITYSCREEN
            18: typeof ScreenAcademic !== 'undefined' ? ScreenAcademic : null,      // SCREEN_ACADEMICSCREEN
            19: typeof ScreenRanking !== 'undefined' ? ScreenRanking : null,        // SCREEN_RANKINGSCREEN
            20: typeof ScreenConsole !== 'undefined' ? ScreenConsole : null,        // SCREEN_CONSOLESCREEN
            21: typeof ScreenSocSec !== 'undefined' ? ScreenSocSec : null,          // SCREEN_SOCSECSCREEN
            22: typeof ScreenLoans !== 'undefined' ? ScreenLoans : null,            // SCREEN_LOANSSCREEN
            23: typeof ScreenSharesList !== 'undefined' ? ScreenSharesList : null,  // SCREEN_SHARESLISTSCREEN
            24: typeof ScreenSharesView !== 'undefined' ? ScreenSharesView : null,  // SCREEN_SHARESVIEWSCREEN
            25: typeof ScreenFaith !== 'undefined' ? ScreenFaith : null,            // SCREEN_FAITHSCREEN
            26: typeof ScreenCypher !== 'undefined' ? ScreenCypher : null,          // SCREEN_CYPHERSCREEN
            27: typeof ScreenVoice !== 'undefined' ? ScreenVoice : null,            // SCREEN_VOICEANALYSIS
            28: typeof ScreenCompanyInfo !== 'undefined' ? ScreenCompanyInfo : null, // SCREEN_COMPANYINFO
            29: typeof ScreenVoicePhone !== 'undefined' ? ScreenVoicePhone : null,  // SCREEN_VOICEPHONE
            30: typeof ScreenHighSecurity !== 'undefined' ? ScreenHighSecurity : null, // SCREEN_HIGHSECURITYSCREEN
            31: typeof ScreenNearestGW !== 'undefined' ? ScreenNearestGW : null,    // SCREEN_NEARESTGATEWAY
            32: typeof ScreenChangeGW !== 'undefined' ? ScreenChangeGW : null,      // SCREEN_CHANGEGATEWAY
            34: typeof ScreenDisconnected !== 'undefined' ? ScreenDisconnected : null, // SCREEN_DISCONNECTEDSCREEN
            35: typeof ScreenProtoVision !== 'undefined' ? ScreenProtoVision : null, // SCREEN_PROTOVISION
            36: typeof ScreenNuclearWar !== 'undefined' ? ScreenNuclearWar : null,  // SCREEN_NUCLEARWAR
            37: typeof ScreenRadioTX !== 'undefined' ? ScreenRadioTX : null,        // SCREEN_RADIOTRANSMITTER
        };

        const renderer = renderers[screen.screen_type];
        if (renderer && typeof renderer.render === 'function') {
            renderer.render(this.panelBody, screen);
        } else {
            this.panelBody.innerHTML = '<div style="color:#ff3333;">Unknown screen type: '
                + screen.screen_type + '</div>';
        }
    }
};
