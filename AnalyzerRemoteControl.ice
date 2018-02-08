#ifndef _ELLISYS_ANALYZER_REMOTE_CONTROL_ICE
#define _ELLISYS_ANALYZER_REMOTE_CONTROL_ICE

module Ellisys
{
	module Platform
	{
		module NetworkRemoteControl
		{
			module Analyzer
			{
				exception OperationFailed { string Reason; };
				
				exception AnalyzerNotFound extends OperationFailed{};
				exception AlreadyRecording extends OperationFailed{};
				exception AlreadyStopped extends OperationFailed{};
				exception UserInteractionPending extends OperationFailed{};
				exception FileSystemError extends OperationFailed{};
				
				const string AnalyzerRemoteControlIdentity = "Ellisys.AnalyzerRemoteControl";
				
				sequence<byte> ByteArray;
				sequence<string> StringArray;
				
				interface AnalyzerRemoteControl
				{
					bool IsRecording() throws OperationFailed;
					void StartRecording() throws OperationFailed;
					void AbortRecordingAndDiscardTraceFile() throws OperationFailed;
					void StopRecordingAndSaveTraceFile(string filename, bool overwrite) throws OperationFailed;
					void ConfigureSettings(ByteArray settings) throws OperationFailed;
					void InsertComment(string comment, string overviewName);

					bool IsLoading() throws OperationFailed;
					void StartLoading(string filename) throws OperationFailed;
					void SelectOverview(string overviewName) throws OperationFailed;
					int OverviewRootItem() throws OperationFailed;
					string GetOverviewItemDescription(int itemHandle) throws OperationFailed;
					long GetOverviewItemTimeInPicoseconds(int itemHandle) throws OperationFailed;
					ByteArray GetOverviewItemData(int itemHandle) throws OperationFailed;
					string GetOverviewItemXmlReport(int itemHandle) throws OperationFailed;
					string GetOverviewItemXmlReportFiltered(int itemHandle, StringArray fieldNameFilters) throws OperationFailed;
					int GetOverviewItemChildCount(int itemHandle) throws OperationFailed;
					int GetOverviewItemChild(int itemHandle, int childIndex) throws OperationFailed;
				};
			};
		};
	};
};

#endif 
