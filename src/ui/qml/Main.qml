import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import "components"

ApplicationWindow {
    id: window

    visible: false
    width: 760
    height: 540
    minimumWidth: 700
    minimumHeight: 500
    color: "transparent"
    title: "Glance"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    required property var settingsController
    required property var iconLibrary
    readonly property var appTheme: theme
    property real dragMouseGlobalX: 0
    property real dragMouseGlobalY: 0
    property real dragWindowX: 0
    property real dragWindowY: 0

    readonly property bool lightTheme: settingsController.settings.theme_preference === "light"

    onActiveChanged: {
        if (!active) {
            hide()
        }
    }

    function beginWindowDrag(item, mouse) {
        var globalPos = item.mapToGlobal(mouse.x, mouse.y)
        dragMouseGlobalX = globalPos.x
        dragMouseGlobalY = globalPos.y
        dragWindowX = window.x
        dragWindowY = window.y
    }

    function updateWindowDrag(item, mouse) {
        if (!(mouse.buttons & Qt.LeftButton)) {
            return
        }

        var globalPos = item.mapToGlobal(mouse.x, mouse.y)
        window.x = dragWindowX + globalPos.x - dragMouseGlobalX
        window.y = dragWindowY + globalPos.y - dragMouseGlobalY
    }

    QtObject {
        id: theme

        readonly property color backgroundBase: lightTheme ? "#f6f5f3" : "#151515"
        readonly property color backgroundPanel: lightTheme ? "#fbfaf8" : "#151515"
        readonly property color sidebarSurface: lightTheme ? "#f4f2ef" : "#101010"
        readonly property color sidebarActiveItem: lightTheme ? "#ece9e5" : "#1e1e1e"
        readonly property color surfaceBase: lightTheme ? "#08000000" : "#08ffffff"
        readonly property color surfaceBaseHover: lightTheme ? "#0d000000" : "#0affffff"
        readonly property color surfaceBaseActive: lightTheme ? "#12000000" : "#0fffffff"
        readonly property color controlSurface: lightTheme ? "#fcfcfc" : "#121212"
        readonly property color controlOutline: lightTheme ? "#e5e5e5" : "#232323"
        readonly property color surfaceOverlaySubtle: lightTheme ? "#fcfcfc" : "#121212"
        readonly property color surfaceRaisedBase: lightTheme ? "#ffffff" : "#0fffffff"
        readonly property color surfaceRaisedBaseActive: lightTheme ? "#ece9e5" : "#1affffff"
        readonly property color surfaceRaisedStronger: lightTheme ? "#ffffff" : "#151515"
        readonly property color surfaceInsetBase: lightTheme ? "#eeebe7" : "#80000000"
        readonly property color inputBase: lightTheme ? "#ffffff" : "#1c1c1c"
        readonly property color textStrong: lightTheme ? "#151311" : "#efffffff"
        readonly property color textBase: lightTheme ? "#6a6763" : "#9effffff"
        readonly property color textWeak: lightTheme ? "#8c8984" : "#6cffffff"
        readonly property color borderBase: lightTheme ? "#20000000" : "#32ffffff"
        readonly property color borderWeakBase: lightTheme ? "#e3dfda" : "#282828"
        readonly property color borderSelected: lightTheme ? "#66635f" : "#9dbefe"
        readonly property color borderWeakSelected: lightTheme ? "#24000000" : "#9e034cff"
        readonly property color buttonPrimaryBase: lightTheme ? "#ece8e3" : "#ededed"
        readonly property color buttonSecondaryBase: lightTheme ? "#ffffff" : "#1c1c1c"
        readonly property color buttonSecondaryHover: lightTheme ? "#f4f1ed" : "#0affffff"
        readonly property color iconBase: lightTheme ? "#83807c" : "#7e7e7e"
        readonly property color iconHover: lightTheme ? "#5f5c58" : "#a0a0a0"
        readonly property color iconStrongBase: lightTheme ? "#171311" : "#ededed"
        readonly property color iconStrongHover: lightTheme ? "#050505" : "#f6f3f3"
        readonly property color iconStrongActive: lightTheme ? "#000000" : "#ffffff"
        readonly property color iconInvertBase: lightTheme ? "#ffffff" : "#161616"
        readonly property color surfaceCriticalWeak: lightTheme ? "#fff7f4" : "#24130f"
        readonly property color borderCriticalSelected: "#fc533a"
        readonly property color textOnCriticalBase: lightTheme ? "#d74c37" : "#fc533a"
        readonly property color surfaceBrandBase: lightTheme ? "#d8d4ce" : "#fab283"
        readonly property color cardShadow: lightTheme ? "#10000000" : "#55000000"
    }

    Rectangle {
        anchors.fill: parent
        radius: 18
        color: theme.backgroundPanel
        border.width: 1
        border.color: theme.borderWeakBase
        opacity: window.visible ? 1 : 0
        scale: window.visible ? 1 : 0.985

        Behavior on opacity { NumberAnimation { duration: 120 } }
        Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.preferredWidth: 178
                Layout.fillHeight: true
                color: theme.sidebarSurface
                radius: 18
                border.width: 1
                border.color: theme.borderWeakBase

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: 12

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton
                            onPressed: window.beginWindowDrag(parent, mouse)
                            onPositionChanged: window.updateWindowDrag(parent, mouse)
                        }
                    }

                    ColumnLayout {
                        spacing: 4
                        Layout.fillWidth: true

                        Text {
                            text: "Desktop"
                            color: theme.textWeak
                            font.pixelSize: 14
                            font.weight: 500
                            leftPadding: 8
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "window-cursor"
                            text: "Capture"
                            selected: settingsController.currentSection === "capture"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("capture")
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "sliders"
                            text: "Audio"
                            selected: settingsController.currentSection === "audio"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("audio")
                        }

                        Item { implicitHeight: 6 }

                        Text {
                            text: "Server"
                            color: theme.textWeak
                            font.pixelSize: 14
                            font.weight: 500
                            leftPadding: 8
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "server"
                            text: "Providers"
                            selected: settingsController.currentSection === "providers"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("providers")
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "glasses"
                            text: "Voice"
                            selected: settingsController.currentSection === "voice"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("voice")
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "shield"
                            text: "Advanced"
                            selected: settingsController.currentSection === "advanced"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("advanced")
                        }

                        Item { implicitHeight: 6 }

                        Text {
                            text: "Data"
                            color: theme.textWeak
                            font.pixelSize: 14
                            font.weight: 500
                            leftPadding: 8
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "task"
                            text: "History"
                            selected: settingsController.currentSection === "history"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("history")
                        }
                    }

                    Item { Layout.fillHeight: true }

                    Rectangle {
                        id: keybindCard
                        Layout.fillWidth: true
                        radius: 12
                        color: theme.surfaceRaisedBase
                        border.width: 1
                        border.color: theme.borderWeakBase
                        implicitHeight: keybindColumn.implicitHeight + 24

                        ColumnLayout {
                            id: keybindColumn
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 4

                            Text {
                                text: "Keybinds"
                                color: theme.textStrong
                                font.pixelSize: 12
                                font.weight: 500
                            }

                            KeybindRow { label: "Live"; value: settingsController.settings.live_keybind || "-"; theme: window.appTheme }
                            KeybindRow { label: "Quick"; value: settingsController.settings.quick_keybind || "-"; theme: window.appTheme }
                            KeybindRow { label: "OCR"; value: settingsController.settings.ocr_keybind || "-"; theme: window.appTheme }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 8
                        spacing: 2

                        Text {
                            text: "Glance"
                            color: theme.textBase
                            font.pixelSize: 12
                            font.weight: 500
                        }

                        Text {
                            text: "0.01"
                            color: theme.textWeak
                            font.pixelSize: 11
                            font.weight: 400
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: theme.backgroundPanel
                radius: 18

                ColumnLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 18
                    anchors.rightMargin: 18
                    anchors.topMargin: 14
                    anchors.bottomMargin: 14
                    spacing: 12

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: 54

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton
                            onPressed: window.beginWindowDrag(parent, mouse)
                            onPositionChanged: window.updateWindowDrag(parent, mouse)
                        }

                        RowLayout {
                            anchors.fill: parent
                            spacing: 12

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: sectionTitle(settingsController.currentSection)
                                    color: theme.textStrong
                                    font.pixelSize: 18
                                    font.weight: 500
                                }

                                Text {
                                    text: sectionDescription(settingsController.currentSection)
                                    color: theme.textBase
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                    Layout.fillWidth: true
                                }
                            }

                            Item {
                                visible: settingsController.saving
                                implicitWidth: 18
                                implicitHeight: 18

                                RotationAnimator on rotation {
                                    from: 0
                                    to: 360
                                    duration: 900
                                    loops: Animation.Infinite
                                    running: settingsController.saving
                                }

                                Canvas {
                                    anchors.fill: parent
                                    onPaint: {
                                        var ctx = getContext("2d")
                                        ctx.reset()
                                        ctx.strokeStyle = theme.iconHover
                                        ctx.lineWidth = 2
                                        ctx.lineCap = "round"
                                        ctx.beginPath()
                                        ctx.arc(width / 2, height / 2, width / 2 - 2, 0.45, 4.9, false)
                                        ctx.stroke()
                                    }
                                }
                            }

                            OcButton {
                                theme: window.appTheme
                                iconLibrary: window.iconLibrary
                                variant: "ghost"
                                iconName: "close-small"
                                text: ""
                                accessibleLabel: "Close"
                                onClicked: window.hide()
                            }
                        }
                    }

                    StatusBanner {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        kind: settingsController.statusKind
                        message: settingsController.statusMessage
                        Layout.fillWidth: true
                        implicitHeight: 42
                    }

                    ScrollView {
                        id: scrollArea
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Item {
                            width: scrollArea.availableWidth
                            implicitHeight: contentColumn.implicitHeight

                            ColumnLayout {
                                id: contentColumn
                                width: Math.min(scrollArea.availableWidth, 640)
                                anchors.horizontalCenter: parent.horizontalCenter
                                spacing: 12

                                Loader {
                                    id: sectionLoader
                                    Layout.fillWidth: true
                                    width: contentColumn.width
                                    sourceComponent: settingsController.currentSection === "providers"
                                        ? providersSection
                                        : settingsController.currentSection === "voice"
                                            ? voiceSection
                                            : settingsController.currentSection === "capture"
                                                    ? captureSection
                                                    : settingsController.currentSection === "audio"
                                                        ? audioSection
                                                        : settingsController.currentSection === "history"
                                                            ? historySection
                                                            : advancedSection

                                    onLoaded: {
                                        if (item) {
                                            item.width = Qt.binding(function() {
                                                return sectionLoader.width
                                            })
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: 14
                        color: theme.surfaceRaisedBase
                        border.width: 1
                        border.color: theme.borderWeakBase

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            OcButton {
                                theme: window.appTheme
                                iconLibrary: window.iconLibrary
                                variant: "primary"
                                iconName: "check"
                                text: "Save"
                                enabled: settingsController.dirty
                                onClicked: settingsController.save()
                            }

                            OcButton {
                                theme: window.appTheme
                                iconLibrary: window.iconLibrary
                                variant: "secondary"
                                iconName: "warning"
                                text: "Validate"
                                onClicked: settingsController.validateDraft()
                            }

                            OcButton {
                                theme: window.appTheme
                                iconLibrary: window.iconLibrary
                                variant: "ghost"
                                iconName: "reset"
                                text: "Reset"
                                enabled: settingsController.dirty
                                onClicked: settingsController.reset()
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: "Theme: " + (settingsController.settings.theme_preference || "dark")
                                color: theme.textWeak
                                font.pixelSize: 13
                                font.weight: 500
                            }
                        }
                    }
                }
            }
        }
    }

    component KeybindRow: RowLayout {
        property string label: ""
        property string value: ""
        property var theme

        Layout.fillWidth: true
        spacing: 8

        Text {
            text: label
            color: theme.textBase
            font.pixelSize: 12
            font.weight: 500
            Layout.preferredWidth: 34
        }

        Rectangle {
            radius: 8
            color: theme.surfaceInsetBase
            border.width: 1
            border.color: theme.borderWeakBase
            implicitHeight: 22
            implicitWidth: Math.min(96, keybindValue.implicitWidth + 16)
            Layout.preferredWidth: Math.min(96, keybindValue.implicitWidth + 16)
            Layout.maximumWidth: 96

            Text {
                id: keybindValue
                anchors.centerIn: parent
                text: value
                color: theme.textStrong
                font.pixelSize: 11
                font.weight: 500
                width: Math.min(80, implicitWidth)
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
        }

        Item { Layout.fillWidth: true }
    }

    Component {
        id: providersSection

        ColumnLayout {
            spacing: 14

            FieldCard {
                theme: window.appTheme
                title: "Wellflow LLM"
                description: "Connection settings for the main reasoning endpoint."
                Layout.fillWidth: true

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "server"
                    label: "Base URL"
                    helperText: "Full endpoint root."
                    errorText: settingsController.errors.llm_base_url || ""
                    value: settingsController.settings.llm_base_url || ""
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("llm_base_url", nextValue) }
                }

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "shield"
                    label: "API key"
                    helperText: "Locally persisted unless seeded from elsewhere."
                    value: settingsController.settings.llm_api_key || ""
                    secret: true
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("llm_api_key", nextValue) }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    LabeledTextField {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "models"
                        label: "Model"
                        helperText: "Current runtime pin."
                        errorText: settingsController.errors.llm_model_name || ""
                        value: settingsController.settings.llm_model_name || ""
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("llm_model_name", nextValue) }
                    }

                    LabeledComboBox {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        label: "Reasoning"
                        helperText: "Stored policy level."
                        value: settingsController.settings.llm_reasoning || "medium"
                        options: settingsController.reasoningOptions
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("llm_reasoning", nextValue) }
                    }
                }
            }
        }
    }

    Component {
        id: voiceSection

        ColumnLayout {
            spacing: 14

            FieldCard {
                theme: window.appTheme
                title: "Speech"
                description: "Compact controls for the TTS endpoint and voice profile."
                Layout.fillWidth: true

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "server"
                    label: "TTS base URL"
                    helperText: "Speech endpoint root."
                    errorText: settingsController.errors.tts_base_url || ""
                    value: settingsController.settings.tts_base_url || ""
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("tts_base_url", nextValue) }
                }

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "shield"
                    label: "TTS API key"
                    helperText: "Used for spoken replies."
                    value: settingsController.settings.tts_api_key || ""
                    secret: true
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("tts_api_key", nextValue) }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    LabeledComboBox {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        label: "Model"
                        helperText: "Speech model."
                        value: settingsController.settings.tts_model || "eleven-v3"
                        options: settingsController.ttsModelOptions
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("tts_model", nextValue) }
                    }

                    LabeledComboBox {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        label: "Voice"
                        helperText: "Voice ID."
                        value: settingsController.settings.tts_voice_id || "alloy"
                        options: settingsController.voiceOptions
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("tts_voice_id", nextValue) }
                    }
                }

                LabeledComboBox {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    label: "Fallback language"
                    helperText: "Used when a request is language-neutral."
                    value: settingsController.settings.fallback_language || "en"
                    options: settingsController.languageOptions
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("fallback_language", nextValue) }
                }
            }
        }
    }

    Component {
        id: captureSection

        ColumnLayout {
            spacing: 14

            FieldCard {
                theme: window.appTheme
                title: "Capture"
                description: "Sampling and deduplication controls for Live mode."
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    LabeledTextField {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "window-cursor"
                        label: "Interval"
                        helperText: "Seconds."
                        errorText: settingsController.errors.screenshot_interval || ""
                        value: String(settingsController.settings.screenshot_interval || "")
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("screenshot_interval", nextValue) }
                    }

                    LabeledTextField {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "models"
                        label: "Threshold"
                        helperText: "0 to 1."
                        errorText: settingsController.errors.screen_change_threshold || ""
                        value: String(settingsController.settings.screen_change_threshold || "")
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("screen_change_threshold", nextValue) }
                    }
                }

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "task"
                    label: "Batch window"
                    helperText: "Seconds grouped into one reply."
                    errorText: settingsController.errors.batch_window_duration || ""
                    value: String(settingsController.settings.batch_window_duration || "")
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("batch_window_duration", nextValue) }
                }
            }
        }
    }

    Component {
        id: audioSection

        ColumnLayout {
            spacing: 14

            FieldCard {
                theme: window.appTheme
                title: "Audio"
                description: "The current build exposes the stable default devices."
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    LabeledComboBox {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        label: "Input"
                        helperText: "Capture route."
                        value: settingsController.settings.audio_input_device || "default"
                        options: settingsController.audioDeviceOptions
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("audio_input_device", nextValue) }
                    }

                    LabeledComboBox {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        label: "Output"
                        helperText: "Playback route."
                        value: settingsController.settings.audio_output_device || "default"
                        options: settingsController.audioDeviceOptions
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("audio_output_device", nextValue) }
                    }
                }
            }
        }
    }

    Component {
        id: historySection

        ColumnLayout {
            spacing: 14

            FieldCard {
                theme: window.appTheme
                title: "History"
                description: "JSON persistence keeps the coursework I/O path explicit and inspectable."
                Layout.fillWidth: true

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "task"
                    label: "History length"
                    helperText: "Maximum stored sessions."
                    errorText: settingsController.errors.history_length || ""
                    value: String(settingsController.settings.history_length || "")
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("history_length", nextValue) }
                }

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: "Clear existing history"
                        color: theme.textStrong
                        font.pixelSize: 13
                        font.weight: 500
                    }

                    Item { Layout.fillWidth: true }

                    OcButton {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        variant: "danger"
                        iconName: "warning"
                        text: "Clear history"
                        onClicked: settingsController.clearHistory()
                    }
                }
            }
        }
    }

    Component {
        id: advancedSection

        ColumnLayout {
            spacing: 14

            FieldCard {
                theme: window.appTheme
                title: "Advanced"
                description: "Runtime appearance and prompt overrides live here."
                Layout.fillWidth: true

                LabeledComboBox {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    label: "Theme preference"
                    helperText: "Light, dark, or system."
                    value: settingsController.settings.theme_preference || "dark"
                    options: settingsController.themeOptions
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("theme_preference", nextValue) }
                }

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "models"
                    label: "System prompt override"
                    helperText: "Optional assistant override."
                    value: settingsController.settings.system_prompt_override || ""
                    multiline: true
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("system_prompt_override", nextValue) }
                }
            }
        }
    }

    function sectionTitle(section) {
        if (section === "providers") return "Providers"
        if (section === "voice") return "Voice"
        if (section === "capture") return "Capture"
        if (section === "audio") return "Audio"
        if (section === "history") return "History"
        return "Advanced"
    }

    function sectionDescription(section) {
        if (section === "providers") return "Keep the model endpoint explicit and easy to verify."
        if (section === "voice") return "Compact TTS controls for spoken replies."
        if (section === "capture") return "Tune Live mode capture cadence and batching."
        if (section === "audio") return "Stable default routing for input and output."
        if (section === "history") return "Local persistence, retention, and safe clearing."
        return "Theme and prompt customization for the runtime."
    }
}
