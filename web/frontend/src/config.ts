export const CONFIG = {
  SCREEN_WIDTH: 1024,
  SCREEN_HEIGHT: 768,

  SERVER_URL: '',  // Same origin, proxied by vite
  WS_URL: `ws://${window.location.host}/ws`,

  // Uplink color palette
  COLORS: {
    BLACK: 0x000000,
    GREEN: 0x00ff41,
    CYAN: 0x00ffff,
    AMBER: 0xffbf00,
    RED: 0xff0000,
    DARK_GREEN: 0x003300,
    DARK_GREY: 0x222222,
    MID_GREY: 0x444444,
    LIGHT_GREY: 0x888888,
    WHITE: 0xffffff,
  },

  // CSS color strings
  COLOR_STR: {
    GREEN: '#00ff41',
    CYAN: '#00ffff',
    AMBER: '#ffbf00',
    RED: '#ff0000',
    DARK_GREEN: '#003300',
    WHITE: '#ffffff',
    BLACK: '#000000',
  },

  // World map dimensions (original Uplink map coords)
  MAP_WIDTH: 595,
  MAP_HEIGHT: 315,
  MAP_OFFSET_X: 10,
  MAP_OFFSET_Y: 50,
  MAP_SCALE: 1.5,

  // HUD
  HUD_HEIGHT: 45,
  TOOLBAR_BUTTONS: ['Software', 'Hardware', 'Status', 'Email', 'Finance', 'Map'],

  // Connection bar
  CONNECTION_BAR_HEIGHT: 30,
};
