#ifndef _ELLISYS_USB30_ANALYZER_REMOTE_CONTROL_ICE
#define _ELLISYS_USB30_ANALYZER_REMOTE_CONTROL_ICE

#include "AnalyzerRemoteControl.ice"

module Ellisys
{
	module Platform
	{
		module NetworkRemoteControl
		{
			module Analyzer
			{
				sequence<byte> LinkKeyByteArray;
				sequence<long> DeviceAddressArray;
				sequence<double> RssiArray;
			
				enum DeviceFilterMode
				{
					KeepAll,
					ExcludeBackground,
					KeepOnly,
					KeepInvolving
				};

				enum LogicSignalTransitionType
				{
					Any,
					RisingEdge, 
					FallingEdge
				};

				interface BluetoothAnalyzerRemoteControl extends AnalyzerRemoteControl
				{
					void SplitTraceFileAndContinueRecording(string filename) throws OperationFailed;

					void AddLinkKey(long bdaddr1, long bdaddr2, LinkKeyByteArray linkKey) throws OperationFailed;

					void SelectProtocolLayer(string protocolLayerName) throws OperationFailed;
					void ConfigureDeviceFilter(DeviceFilterMode mode, DeviceAddressArray deviceAddrs) throws OperationFailed;

					void GetLogicSignalsState(long timeInPicoseconds, out int logicSignalsState) throws OperationFailed;
					void FindLogicSignalsTransition(long fromTimeInPicoseconds, long toTimeInPicoseconds, int signalsMask, LogicSignalTransitionType transitionType, out int foundLogicSignalsState, out long foundTimeInPicoseconds) throws OperationFailed;

					void GetSpectrumRssi(long timeInPicoseconds, int rfChannelNumber, out double rssi, out long startTimeInPicoseconds, out long stopTimeInPicoseconds) throws OperationFailed;
					void GetSpectrumRssiRange(long fromTimeInPicoseconds, long toTimeInPicoseconds, int rfChannelNumber, out RssiArray rssi, out long startTimeInPicoseconds, out long stopTimeInPicoseconds) throws OperationFailed;

					void ExportAudio(string outputDirectory);
				};
			};
		};
	};
};

#endif 
