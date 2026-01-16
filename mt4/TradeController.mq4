//+------------------------------------------------------------------+
//|                                              TradeController.mq4 |
//|                                       MonitoringIndicator System |
//|                         Controls trade execution via config file |
//+------------------------------------------------------------------+
#property copyright "MonitoringIndicator"
#property link      ""
#property version   "1.00"
#property strict

//--- Input parameters
input bool   TradeEnabled = true;    // Enable MT5 Trade Execution
input int    UpdateInterval = 1;     // Update interval (seconds)
input string ControlFileName = "trade_control.json";  // Control file name

//--- Global variables
datetime lastUpdate = 0;
bool lastState = true;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Set timer for periodic updates
   EventSetTimer(UpdateInterval);

   //--- Initial file write
   WriteControlFile();

   //--- Create visual indicator on chart
   CreateStatusLabel();
   UpdateStatusLabel();

   Print("TradeController initialized. TradeEnabled=", TradeEnabled);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   //--- Remove timer
   EventKillTimer();

   //--- Remove chart objects
   ObjectDelete(0, "TradeStatusLabel");
   ObjectDelete(0, "TradeStatusBg");

   Print("TradeController deinitialized. Reason=", reason);
}

//+------------------------------------------------------------------+
//| Timer function                                                     |
//+------------------------------------------------------------------+
void OnTimer()
{
   //--- Check if state changed
   if(lastState != TradeEnabled)
   {
      WriteControlFile();
      UpdateStatusLabel();
      lastState = TradeEnabled;
      Print("Trade state changed to: ", TradeEnabled ? "ENABLED" : "DISABLED");
   }
}

//+------------------------------------------------------------------+
//| Expert tick function (backup update)                               |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Update on tick as backup (in case timer fails)
   if(TimeCurrent() - lastUpdate > UpdateInterval)
   {
      if(lastState != TradeEnabled)
      {
         WriteControlFile();
         UpdateStatusLabel();
         lastState = TradeEnabled;
      }
      lastUpdate = TimeCurrent();
   }
}

//+------------------------------------------------------------------+
//| Write control file                                                 |
//+------------------------------------------------------------------+
void WriteControlFile()
{
   int handle = FileOpen(ControlFileName, FILE_WRITE|FILE_TXT|FILE_ANSI);

   if(handle != INVALID_HANDLE)
   {
      string json = "{";
      json += "\"enabled\": " + (TradeEnabled ? "true" : "false") + ",";
      json += "\"updated_at\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",";
      json += "\"source\": \"MT4_EA\"";
      json += "}";

      FileWriteString(handle, json);
      FileClose(handle);

      lastUpdate = TimeCurrent();
   }
   else
   {
      Print("Error opening control file: ", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Create status label on chart                                       |
//+------------------------------------------------------------------+
void CreateStatusLabel()
{
   //--- Background rectangle
   ObjectCreate(0, "TradeStatusBg", OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "TradeStatusBg", OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, "TradeStatusBg", OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, "TradeStatusBg", OBJPROP_YDISTANCE, 30);
   ObjectSetInteger(0, "TradeStatusBg", OBJPROP_XSIZE, 180);
   ObjectSetInteger(0, "TradeStatusBg", OBJPROP_YSIZE, 30);
   ObjectSetInteger(0, "TradeStatusBg", OBJPROP_BGCOLOR, clrBlack);
   ObjectSetInteger(0, "TradeStatusBg", OBJPROP_BORDER_TYPE, BORDER_FLAT);

   //--- Status text
   ObjectCreate(0, "TradeStatusLabel", OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, "TradeStatusLabel", OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, "TradeStatusLabel", OBJPROP_XDISTANCE, 20);
   ObjectSetInteger(0, "TradeStatusLabel", OBJPROP_YDISTANCE, 35);
   ObjectSetString(0, "TradeStatusLabel", OBJPROP_FONT, "Arial Bold");
   ObjectSetInteger(0, "TradeStatusLabel", OBJPROP_FONTSIZE, 12);
}

//+------------------------------------------------------------------+
//| Update status label                                                |
//+------------------------------------------------------------------+
void UpdateStatusLabel()
{
   if(TradeEnabled)
   {
      ObjectSetString(0, "TradeStatusLabel", OBJPROP_TEXT, "MT5 Trade: ON");
      ObjectSetInteger(0, "TradeStatusLabel", OBJPROP_COLOR, clrLime);
      ObjectSetInteger(0, "TradeStatusBg", OBJPROP_BGCOLOR, clrDarkGreen);
   }
   else
   {
      ObjectSetString(0, "TradeStatusLabel", OBJPROP_TEXT, "MT5 Trade: OFF");
      ObjectSetInteger(0, "TradeStatusLabel", OBJPROP_COLOR, clrRed);
      ObjectSetInteger(0, "TradeStatusBg", OBJPROP_BGCOLOR, clrDarkRed);
   }
   ChartRedraw(0);
}
//+------------------------------------------------------------------+
