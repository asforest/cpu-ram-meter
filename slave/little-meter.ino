#include "Wire.h"
#include "U8g2lib.h"
#include "ArduinoJson.h"
#include <EEPROM.h>
#if defined(ARDUINO_ESP8266_RELEASE)
#include <ESP8266WiFi.h>
#elif defined(ARDUINO_ESP32_RELEASE)
#include <WiFi.h>
#else
#error "The ESP8266 or the ESP32 environment is required to compile."
#endif

struct WifiConfig {
    char ssid[32];
    char password[32];
    unsigned long is_set;
};

struct BrightnessConfig {
    byte brightness;
    unsigned long is_set;
};

const byte address = 0x3c;
const int screen_width = 128;
const int screen_height = 32;
int network_port = 9080;

char* ssid = NULL;
char* password = NULL;
const int ssid_password_length = 32;
const byte eeprom_default_value = 0;
const int screen_buf_len = screen_width * screen_height / 8;
const int tcp_buf_len = screen_width * screen_height / 8 + 1;
const int serial_buf_len = 128;
byte screen_buf[screen_buf_len];
byte tcp_buf[tcp_buf_len];
byte serial_buf[serial_buf_len];
char shared_string_buf[128];
bool screen_buf_has_contents = false;
unsigned long last_rssi_refresh = 0;
wl_status_t last_wifi_state = WL_NO_SHIELD;

//U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);
U8G2_SSD1306_128X32_UNIVISION_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);
WiFiServer server(network_port);
DynamicJsonDocument json_doc(1024);

void write_ssid_password(char* ssid, char* password)
{
    WifiConfig data;
    memset(&data, 0, sizeof(WifiConfig));
    memcpy(&data.ssid, ssid, strlen(ssid));
    memcpy(&data.password, password, strlen(password));
    data.is_set = 0x12345678UL;
    EEPROM.put(0, data);
    EEPROM.commit();
}

WifiConfig read_ssid_password()
{
    WifiConfig data;
    memset(&data, 0, sizeof(WifiConfig));
    EEPROM.get(0, data);
    return data;
}

bool is_ssid_password_set()
{
    WifiConfig wc = read_ssid_password();
    return wc.is_set == 0x12345678UL;
}

void write_brightness(byte brightness)
{
    int addr = sizeof(WifiConfig);
    BrightnessConfig bc;
    memset(&bc, 0, sizeof(BrightnessConfig));
    bc.brightness = brightness;
    bc.is_set = 0x12345678UL;
    EEPROM.put(addr, brightness);
    EEPROM.commit();
}

byte read_brightness()
{
    int addr = sizeof(WifiConfig);
    BrightnessConfig bc;
    EEPROM.get(addr, bc);
    return bc.is_set == 0x12345678UL ? bc.brightness : 255;
}

void rtrim(char* str)
{
    int len = strlen(str);
    char* p = str + len - 1;
    while(isspace(*p) && p >= str)        
         p -= 1;
    *(p + 1) = 0;
}

void print_tcp_buf()
{
    // print to Serial
    for (int y=0;y<screen_height;y++)
    {
        for (int x=0;x<screen_width;x++)
        {
            int byte_idx = (x + y * screen_width) / 8;
            int bit_idx = (x + y * screen_width) % 8;
//            Serial.printf("%c/%02x(%d:%d)/", screen_buf[byte_idx], screen_buf[byte_idx], byte_idx, bit_idx);
            
            bool pixel = (tcp_buf[byte_idx] & (0x80 >> (bit_idx))) > 0;
            Serial.print(pixel ? "@" : ".");
        }
        Serial.print('\n');
    }
}

void draw_screen_frame()
{
    if (!screen_buf_has_contents)
        return;
    
    u8g2.clearBuffer();
    u8g2.drawBitmap(0, 0, screen_width / 8, screen_height, screen_buf);
    u8g2.sendBuffer();
}

void display_text(char* line0, char* line1=NULL)
{
    String l0(line0);
    String l1(line1);

    l0.replace(" ", "   ");
    l1.replace(" ", "   ");
    
    u8g2.clearBuffer();
    u8g2.drawUTF8(0, 0, l0.c_str());
    if (line1 != NULL)
      u8g2.drawUTF8(0, 16, l1.c_str());
    u8g2.sendBuffer();
}

void process_client()
{
    WiFiClient client = server.available();

    if (client)
    {
        client.setTimeout(0);
        Serial.printf("new client from %s\n", client.remoteIP().toString().c_str());

        while (client.connected())
        {
            // if there are bytes abvailable to read
            if (client.available())
            {
//                memset(tcp_buf, 0, tcp_buf_len);
                int received = 0;
                bool no_data = false;

                // collect all the data available
                while (true) 
                {
                    if (client.available())
                    {
                        // receive all the expected data from the Serial
                        int read = (int) client.readBytes(tcp_buf + received, 16);
                        received += read;
                        if (received > tcp_buf_len)
                            break;
                        no_data = false;
                    } else {
                        if (no_data)
                          break;
                        no_data = true;
                        delay(100);
                    }
                }

                // detect the first byte
                char first = (char) tcp_buf[0];
                int payload_len = received - 1;
                byte* payload = tcp_buf + 1;
                int expected = 0;

                switch (first)
                {
                    case 'b': // screen Buffer writing command
                        if (payload_len >= screen_buf_len)
                        {
                            screen_buf_has_contents = true;
                            memcpy(screen_buf, payload, screen_buf_len);
                            draw_screen_frame();

                            client.printf("ok\n");
                            client.flush();
                        } else {
                            expected = screen_buf_len;
                        }
                        break;

                    case 'c': // set the oled Contrast
                        if (payload_len >= 1)
                        {
                            byte brightness = payload[0];
                            write_brightness(brightness);
                            u8g2.setContrast(brightness);
                        } else {
                            expected = 1;
                        }
                        break;

                    case 'r': // Restart the chip
                        ESP.restart();
                        break;
                        
                    default:
                        client.printf("unknown command: %c\n", first);
                        client.flush();
                        break;
                }

                if (expected > 0)
                {
                    client.printf("%c: expect data len %d, received len %d.\n", first, payload_len, expected);
                    client.flush();
                }
            }
        }

        client.stop();
        Serial.printf("client disconnected from %s\n", client.remoteIP().toString().c_str());
        screen_buf_has_contents = false;
        memset(screen_buf, 0, screen_buf_len);
    }
}

void process_serial()
{
    if (!Serial.available())
        return;

    memset(serial_buf, 0, serial_buf_len);
    
    int received = 0;

    // receive all the data
    while(true)
    {
        int read = (int) Serial.readBytes(serial_buf + received, 16);
        if (read == 0)
            break;
        received += read;
    }

    if (received = 0)
        return;

    Serial.printf("%s\n", (char*) serial_buf);

    String raw((char*) serial_buf);
    DeserializationError err = deserializeJson(json_doc, (char*) serial_buf);
    if (err != DeserializationError::Ok)
    {
        Serial.printf("input data failed to be deserialized into json format: %s\n", raw.c_str());
        return;
    }
    
    if (!json_doc.containsKey("ssid"))
    {
        Serial.printf("the field 'ssid' did not present in the json format: %s\n", raw.c_str());
        return;
    }

    if (!json_doc.containsKey("password"))
    {
        Serial.printf("the field 'password' did not present in the json format: %s\n", raw.c_str());
        return;
    }

    const char* ssid = json_doc["ssid"];
    const char* password = json_doc["password"];

    if (strlen(ssid) == 0 || strlen(ssid) > 16)
    {
        Serial.printf("the length of the field 'ssid' is only allowed within 0 - 16\n");
        return;
    }

    if (strlen(password) == 0 || strlen(password) > 16)
    {
        Serial.printf("the length of the field 'password' is only allowed within 0 - 16\n");
        return;
    }

    Serial.printf("set new ssid: %s(%d), password: %s(%d)\n", ssid, strlen(ssid), password, strlen(password));

    write_ssid_password((char*) ssid, (char*) password);
    delay(100);
    ESP.restart();
}

void show_message()
{
    if (ssid == NULL || password == NULL)
    {
        display_text("ssid not specified", "over UART");
        return;
    }

    bool state_changed = WiFi.status() != last_wifi_state;
    
    switch (WiFi.status())
    {
        case WL_IDLE_STATUS:
            if (!state_changed)
                return;
            
            display_text("searching for signal", ssid);
            break;

        case WL_NO_SSID_AVAIL:
            if (!state_changed)
                return;
            
            display_text("no ssid signal available", ssid);
            break;

        case WL_CONNECTED:
            if (last_wifi_state != WL_CONNECTED)
            {
                last_rssi_refresh = 0;
                
                Serial.printf("ip address: %s\n", WiFi.localIP().toString().c_str());
            
                // start the TCP server
                server.begin();
            }
            
            if (millis() - last_rssi_refresh > 1500 && !screen_buf_has_contents)
            {
                char rssi[16];
                sprintf(rssi, "RSSI: %d", WiFi.RSSI());
                sprintf(shared_string_buf, "%s:%d", WiFi.localIP().toString().c_str(), network_port);
                display_text(shared_string_buf, rssi);
                last_rssi_refresh = millis();
            }
            
            break;

        case WL_DISCONNECTED:
            if (!state_changed)
                return;
            
            // stop the TCP server
            server.close();

            screen_buf_has_contents = false;
            
            display_text("wifi disconnected", ssid);
            break;
    }
    
    last_wifi_state = WiFi.status();
}

void setup()
{
    Serial.begin(115200);
    Serial.setTimeout(100); // set timeout for reading
    
    EEPROM.begin(128);

    // initialize i2c
    Wire.begin();
    Wire.setClock(400000);

    // make sure the connection with OLED
    Wire.beginTransmission(address);
    byte error = Wire.endTransmission();
    if (error != 0)
    {
        Serial.printf("failed to communicate with OLED, reset...");
        delay(800);
        ESP.restart();
    }

    // initialize the oled display
    u8g2.begin();
    u8g2.setFontPosTop();
    u8g2.setFont(u8g2_font_nine_by_five_nbp_tf);

    // clear the screen buffer
    memset(screen_buf, 0, screen_buf_len);

    // load oled preferences from flash
    byte brightness = read_brightness();
    u8g2.setContrast(brightness);
    Serial.printf("set oled brightness to %d\n", brightness);

    // load wifi preferences from flash
    if (is_ssid_password_set())
    {
        ssid = new char[ssid_password_length];
        password = new char[ssid_password_length];
        memset(ssid, 0, ssid_password_length);
        memset(password, 0, ssid_password_length);
        
        WifiConfig wc = read_ssid_password();
        memcpy(ssid, wc.ssid, strlen(wc.ssid));
        memcpy(password, wc.password, strlen(wc.password));
        Serial.printf("wifi preferences loaded: %s, %s\n", ssid, password);
    }

    // connect to the network
    if (ssid != NULL && password != NULL) 
        WiFi.begin(ssid, password);
}

void loop() 
{
    show_message();
    
    if (WiFi.status() == WL_CONNECTED)
        process_client();

    process_serial();

    delay(10);
}