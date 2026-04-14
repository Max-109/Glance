import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import "components"

ApplicationWindow {
    id: window

    visible: false
    width: 840
    height: 680
    minimumWidth: 780
    minimumHeight: 625
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
        readonly property color borderHover: lightTheme ? "#3c000000" : "#48ffffff"
        readonly property color borderWeakBase: lightTheme ? "#e3dfda" : "#282828"
        readonly property color borderSelected: lightTheme ? "#66635f" : "#9dbefe"
        readonly property color borderWeakSelected: lightTheme ? "#24000000" : "#9e034cff"
        readonly property color buttonPrimaryBase: lightTheme ? "#ece8e3" : "#ededed"
        readonly property color buttonPrimaryHover: lightTheme ? "#151313" : "#f6f3f3"
        readonly property color buttonPrimaryActive: lightTheme ? "#020202" : "#fcfcfc"
        readonly property color buttonSecondaryBase: lightTheme ? "#ffffff" : "#1c1c1c"
        readonly property color buttonSecondaryHover: lightTheme ? "#f4f1ed" : "#0affffff"
        readonly property color buttonSecondaryDisabled: lightTheme ? "#ededed" : "#282828"
        readonly property color iconBase: lightTheme ? "#83807c" : "#7e7e7e"
        readonly property color iconHover: lightTheme ? "#5f5c58" : "#a0a0a0"
        readonly property color iconActive: lightTheme ? "#171717" : "#ededed"
        readonly property color iconDisabled: lightTheme ? "#c7c7c7" : "#3e3e3e"
        readonly property color iconStrongBase: lightTheme ? "#171311" : "#ededed"
        readonly property color iconStrongHover: lightTheme ? "#050505" : "#f6f3f3"
        readonly property color iconStrongActive: lightTheme ? "#000000" : "#ffffff"
        readonly property color iconStrongDisabled: lightTheme ? "#c7c7c7" : "#3e3e3e"
        readonly property color iconInvertBase: lightTheme ? "#ffffff" : "#161616"
        readonly property color surfaceCriticalWeak: lightTheme ? "#fff7f4" : "#24130f"
        readonly property color borderCriticalSelected: "#fc533a"
        readonly property color textOnCriticalBase: lightTheme ? "#d74c37" : "#fc533a"
        readonly property color surfaceBrandBase: lightTheme ? "#d8d4ce" : "#fab283"
        readonly property color cardShadow: lightTheme ? "#10000000" : "#55000000"
    }

    Rectangle {
        id: shell
        anchors.fill: parent
        focus: settingsController.bindingActive
        Keys.onPressed: function(event) {
            if (!settingsController.bindingActive) {
                return
            }
            settingsController.captureKeybind(event.key, event.modifiers, event.text)
            event.accepted = true
        }
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
                Layout.preferredWidth: 205
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
                            text: "Input"
                            color: theme.textWeak
                            font.pixelSize: 14
                            font.weight: 500
                            leftPadding: 8
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "scan-search"
                            text: "Capture"
                            selected: settingsController.currentSection === "capture"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("capture")
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "audio-lines"
                            text: "Audio"
                            selected: settingsController.currentSection === "audio"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("audio")
                        }

                        Item { implicitHeight: 6 }

                        Text {
                            text: "Runtime"
                            color: theme.textWeak
                            font.pixelSize: 14
                            font.weight: 500
                            leftPadding: 8
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "link-2"
                            text: "API"
                            selected: settingsController.currentSection === "api"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("api")
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "speech"
                            text: "Speech"
                            selected: settingsController.currentSection === "voice"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("voice")
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "settings-2"
                            text: "General"
                            selected: settingsController.currentSection === "advanced"
                            Layout.fillWidth: true
                            onClicked: settingsController.setCurrentSection("advanced")
                        }

                        Item { implicitHeight: 6 }

                        Text {
                            text: "Storage"
                            color: theme.textWeak
                            font.pixelSize: 14
                            font.weight: 500
                            leftPadding: 8
                        }

                        SidebarItem {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            iconName: "history"
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
                                text: "Shortcuts"
                                color: theme.textStrong
                                font.pixelSize: 12
                                font.weight: 500
                            }

                            Text {
                                text: settingsController.bindingActive
                                    ? "Capture mode is active. Press a shortcut, or Escape to cancel."
                                    : "Click a row to override the shortcut."
                                color: settingsController.bindingActive ? theme.textStrong : theme.textWeak
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }

                            KeybindRow {
                                label: "Live"
                                value: settingsController.settings.live_keybind || "-"
                                theme: window.appTheme
                                captureField: "live_keybind"
                                captureActive: settingsController.bindingField === captureField
                                onClicked: {
                                    settingsController.startKeybindCapture(captureField)
                                    shell.forceActiveFocus()
                                }
                            }
                            KeybindRow {
                                label: "Quick"
                                value: settingsController.settings.quick_keybind || "-"
                                theme: window.appTheme
                                captureField: "quick_keybind"
                                captureActive: settingsController.bindingField === captureField
                                onClicked: {
                                    settingsController.startKeybindCapture(captureField)
                                    shell.forceActiveFocus()
                                }
                            }
                            KeybindRow {
                                label: "OCR"
                                value: settingsController.settings.ocr_keybind || "-"
                                theme: window.appTheme
                                captureField: "ocr_keybind"
                                captureActive: settingsController.bindingField === captureField
                                onClicked: {
                                    settingsController.startKeybindCapture(captureField)
                                    shell.forceActiveFocus()
                                }
                            }
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
                            text: "v0.1 Alpha"
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
                                iconName: "x"
                                text: ""
                                accessibleLabel: "Close settings"
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
                                width: Math.min(scrollArea.availableWidth, 720)
                                anchors.horizontalCenter: parent.horizontalCenter
                                spacing: 12

                                Loader {
                                    id: sectionLoader
                                    Layout.fillWidth: true
                                    width: contentColumn.width
                                    sourceComponent: settingsController.currentSection === "api"
                                        ? apiSection
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
                                iconName: "circle-question-mark"
                                text: "Check settings"
                                onClicked: settingsController.validateDraft()
                            }

                            OcButton {
                                theme: window.appTheme
                                iconLibrary: window.iconLibrary
                                variant: "ghost"
                                iconName: "rotate-ccw"
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
        id: keybindRowRoot
        property string label: ""
        property string value: ""
        property string captureField: ""
        property bool captureActive: false
        property var theme
        readonly property string displayValue: captureActive
            ? "PRESS SHORTCUT"
            : (value && value.length > 0 ? value : "-")

        signal clicked()

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
            radius: 10
            color: captureActive ? theme.surfaceRaisedBaseActive : theme.surfaceInsetBase
            border.width: 1
            border.color: captureActive ? theme.borderBase : theme.borderWeakBase
            implicitHeight: 28
            implicitWidth: Math.min(200, keybindValue.implicitWidth + 20)
            Layout.preferredWidth: Math.min(200, keybindValue.implicitWidth + 20)
            Layout.maximumWidth: 200

            Behavior on color { ColorAnimation { duration: 120 } }
            Behavior on border.color { ColorAnimation { duration: 120 } }

            Text {
                id: keybindValue
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                text: keybindRowRoot.displayValue
                color: theme.textStrong
                font.pixelSize: 11
                font.weight: 600
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: keybindRowRoot.clicked()
            }
        }

        Item { Layout.fillWidth: true }
    }

    component ApiTabButton: Button {
        id: apiTabButton

        property var theme
        property bool selected: false

        implicitHeight: 34
        hoverEnabled: true
        Accessible.name: text

        contentItem: Text {
            text: apiTabButton.text
            color: apiTabButton.selected ? theme.textStrong : theme.textBase
            font.pixelSize: 13
            font.weight: 600
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            radius: 8
            color: apiTabButton.selected
                ? theme.surfaceRaisedBaseActive
                : (apiTabButton.hovered ? theme.surfaceBaseHover : "transparent")
            border.width: apiTabButton.selected ? 1 : 0
            border.color: apiTabButton.selected ? theme.controlOutline : "transparent"

            Behavior on color { ColorAnimation { duration: 140 } }
            Behavior on border.color { ColorAnimation { duration: 140 } }
        }
    }

    Component {
        id: apiSection

        ColumnLayout {
            id: apiSectionRoot
            property string currentApiPanel: "llm"
            spacing: 14

            FieldCard {
                theme: window.appTheme
                title: "Providers"
                description: "Different settings for different parts of pipeline."
                Layout.fillWidth: true

                Rectangle {
                    Layout.fillWidth: true
                    radius: 10
                    color: theme.surfaceBase
                    border.width: 1
                    border.color: theme.borderWeakBase
                    implicitHeight: apiTabRow.implicitHeight + 12

                    RowLayout {
                        id: apiTabRow
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 6

                        ApiTabButton {
                            theme: window.appTheme
                            text: "LLM"
                            selected: apiSectionRoot.currentApiPanel === "llm"
                            Layout.fillWidth: true
                            onClicked: apiSectionRoot.currentApiPanel = "llm"
                        }

                        ApiTabButton {
                            theme: window.appTheme
                            text: "Speech Engine"
                            selected: apiSectionRoot.currentApiPanel === "speech"
                            Layout.fillWidth: true
                            onClicked: apiSectionRoot.currentApiPanel = "speech"
                        }

                        ApiTabButton {
                            theme: window.appTheme
                            text: "Transcription"
                            selected: apiSectionRoot.currentApiPanel === "transcription"
                            Layout.fillWidth: true
                            onClicked: apiSectionRoot.currentApiPanel = "transcription"
                        }
                    }
                }

                Loader {
                    Layout.fillWidth: true
                    sourceComponent: apiSectionRoot.currentApiPanel === "llm"
                        ? llmApiPanel
                        : apiSectionRoot.currentApiPanel === "speech"
                            ? speechEngineApiPanel
                            : transcriptionApiPanel
                }
            }
        }
    }

    Component {
        id: llmApiPanel

        ColumnLayout {
            spacing: 12

            LabeledTextField {
                theme: window.appTheme
                iconLibrary: window.iconLibrary
                iconName: "link-2"
                label: "Base URL"
                helperText: "Full URL for your LLM API endpoint."
                errorText: settingsController.errors.llm_base_url || ""
                value: settingsController.settings.llm_base_url || ""
                Layout.fillWidth: true
                onValueEdited: function(nextValue) { settingsController.setField("llm_base_url", nextValue) }
            }

            LabeledTextField {
                theme: window.appTheme
                iconLibrary: window.iconLibrary
                iconName: "key-round"
                label: "Key for the API"
                helperText: "Saved locally on this device."
                value: settingsController.settings.llm_api_key || ""
                secret: true
                Layout.fillWidth: true
                onValueEdited: function(nextValue) { settingsController.setField("llm_api_key", nextValue) }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "bot"
                    label: "Model"
                    helperText: "Model name to use for responses."
                    errorText: settingsController.errors.llm_model_name || ""
                    value: settingsController.settings.llm_model_name || ""
                    Layout.fillWidth: true
                    Layout.preferredWidth: 3
                    Layout.minimumWidth: 0
                    onValueEdited: function(nextValue) { settingsController.setField("llm_model_name", nextValue) }
                }

                LabeledComboBox {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "gauge"
                    label: "Reasoning"
                    helperText: "Reasoning effort for replies."
                    value: settingsController.settings.llm_reasoning || "medium"
                    options: settingsController.reasoningOptions
                    optionIcons: ({
                        "minimal": "clock-3",
                        "low": "zap",
                        "medium": "brain",
                        "high": "brain-circuit"
                    })
                    Layout.fillWidth: true
                    Layout.preferredWidth: 2
                    Layout.minimumWidth: 0
                    onValueEdited: function(nextValue) { settingsController.setField("llm_reasoning", nextValue) }
                }
            }
        }
    }

    Component {
        id: transcriptionApiPanel

        ColumnLayout {
            spacing: 12

            LabeledTextField {
                theme: window.appTheme
                iconLibrary: window.iconLibrary
                iconName: "link-2"
                label: "Base URL"
                helperText: "Full URL for your transcription API endpoint."
                errorText: settingsController.errors.transcription_base_url || ""
                value: settingsController.settings.transcription_base_url || ""
                Layout.fillWidth: true
                onValueEdited: function(nextValue) { settingsController.setField("transcription_base_url", nextValue) }
            }

            LabeledTextField {
                theme: window.appTheme
                iconLibrary: window.iconLibrary
                iconName: "key-round"
                label: "Key for the API"
                helperText: "Saved locally on this device."
                value: settingsController.settings.transcription_api_key || ""
                secret: true
                Layout.fillWidth: true
                onValueEdited: function(nextValue) { settingsController.setField("transcription_api_key", nextValue) }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "audio-lines"
                    label: "Model"
                    helperText: "A model which is used for transcribing."
                    errorText: settingsController.errors.transcription_model_name || ""
                    value: settingsController.settings.transcription_model_name || "gemini-3.1-flash-lite-preview"
                    Layout.fillWidth: true
                    Layout.preferredWidth: 3
                    Layout.minimumWidth: 0
                    onValueEdited: function(nextValue) { settingsController.setField("transcription_model_name", nextValue) }
                }

                LabeledComboBox {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "zap"
                    label: "Reasoning"
                    helperText: "Reasoning effort per turn."
                    value: settingsController.settings.transcription_reasoning || "medium"
                    options: settingsController.transcriptionReasoningOptions
                    optionIcons: ({
                        "minimal": "zap",
                        "low": "zap",
                        "medium": "brain",
                        "high": "brain-circuit"
                    })
                    Layout.fillWidth: true
                    Layout.preferredWidth: 2
                    Layout.minimumWidth: 0
                    onValueEdited: function(nextValue) { settingsController.setField("transcription_reasoning", nextValue) }
                }
            }
        }
    }

    Component {
        id: speechEngineApiPanel

        ColumnLayout {
            spacing: 12

            LabeledTextField {
                theme: window.appTheme
                iconLibrary: window.iconLibrary
                iconName: "link-2"
                label: "Base URL"
                helperText: "Full URL for your speech API endpoint."
                errorText: settingsController.errors.tts_base_url || ""
                value: settingsController.settings.tts_base_url || ""
                Layout.fillWidth: true
                onValueEdited: function(nextValue) { settingsController.setField("tts_base_url", nextValue) }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "key-round"
                    label: "Key for the API"
                    helperText: "Saved locally on this device."
                    value: settingsController.settings.tts_api_key || ""
                    secret: true
                    Layout.fillWidth: true
                    Layout.preferredWidth: 3
                    Layout.minimumWidth: 0
                    onValueEdited: function(nextValue) { settingsController.setField("tts_api_key", nextValue) }
                }

                LabeledComboBox {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "speech"
                    label: "Model"
                    helperText: "Speech generation model."
                    value: settingsController.settings.tts_model || "eleven-v3"
                    options: settingsController.ttsModelOptions
                    Layout.fillWidth: true
                    Layout.preferredWidth: 2
                    Layout.minimumWidth: 0
                    onValueEdited: function(nextValue) { settingsController.setField("tts_model", nextValue) }
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
                description: "Choose how Glance should sound when it speaks back."
                Layout.fillWidth: true

                VoiceSelectionRow {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    label: "Voice"
                    helperText: "Auto picks the best curated Eleven v3 voice for each reply. Use the play button to preview a fixed voice."
                    value: settingsController.settings.tts_voice_id || settingsController.voiceOptions[0]
                    options: settingsController.voiceOptions
                    optionLabels: settingsController.voiceOptionLabels
                    previewingVoice: settingsController.previewingVoice || ""
                    previewEnabled: (settingsController.settings.tts_voice_id || settingsController.voiceOptions[0]) !== "auto"
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("tts_voice_id", nextValue) }
                    onPreviewClicked: function(voiceName) { settingsController.previewVoice(voiceName) }
                }

                LabeledComboBox {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "languages"
                    label: "Fallback language"
                    helperText: "Used when the reply should be spoken in a default language."
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
                description: "Control how often Glance checks the screen and groups updates."
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    LabeledTextField {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "clock-3"
                        label: "Capture interval"
                        helperText: "How often Glance checks the screen, in seconds."
                        errorText: settingsController.errors.screenshot_interval || ""
                        value: String(settingsController.settings.screenshot_interval || "")
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("screenshot_interval", nextValue) }
                    }

                    LabeledTextField {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "gauge"
                        label: "Change threshold"
                        helperText: "How much the screen must change before Glance reacts."
                        errorText: settingsController.errors.screen_change_threshold || ""
                        value: String(settingsController.settings.screen_change_threshold || "")
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("screen_change_threshold", nextValue) }
                    }
                }

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "history"
                    label: "Batch window"
                    helperText: "How long to group updates into one reply, in seconds."
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
                title: "Devices"
                description: "Choose the hardware Glance should use for listening and playback."
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    LabeledComboBox {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "mic"
                        label: "Input device"
                        helperText: "Microphone used for live mode and the local mic test."
                        value: settingsController.settings.audio_input_device || "default"
                        options: settingsController.audioInputDeviceOptions
                        optionLabels: settingsController.audioInputDeviceLabels
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("audio_input_device", nextValue) }
                    }

                    LabeledComboBox {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "headphones"
                        label: "Output device"
                        helperText: "Speaker or headphones used for live replies, voice preview, and the speaker test."
                        value: settingsController.settings.audio_output_device || "default"
                        options: settingsController.audioOutputDeviceOptions
                        optionLabels: settingsController.audioOutputDeviceLabels
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("audio_output_device", nextValue) }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        OcButton {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            variant: "secondary"
                            iconName: "rotate-ccw"
                            text: "Refresh devices"
                            onClicked: settingsController.refreshAudioDevices()
                        }

                        OcButton {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            variant: "secondary"
                            iconName: settingsController.speakerTestActive ? "audio-lines" : "play"
                            text: settingsController.speakerTestActive ? "Stop speaker test" : "Play speaker test"
                            onClicked: {
                                if (settingsController.speakerTestActive) {
                                    settingsController.stopSpeakerTest()
                                } else {
                                    settingsController.playSpeakerTest()
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: settingsController.audioDeviceStatusMessage
                            color: theme.textWeak
                            font.pixelSize: 13
                            font.weight: 400
                            wrapMode: Text.Wrap
                            horizontalAlignment: Text.AlignRight
                            Layout.preferredWidth: 250
                        }
                    }
                }
            }

            FieldCard {
                theme: window.appTheme
                title: "Mic Calibration"
                description: "Test the microphone and drag the trigger marker until normal speech crosses it without reacting to room noise."
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    AudioLevelMeter {
                        theme: window.appTheme
                        level: settingsController.audioInputLevel
                        threshold: Number(settingsController.settings.audio_activation_threshold || 0.02)
                        active: settingsController.audioInputTestActive
                        editable: true
                        Layout.fillWidth: true
                        onThresholdEdited: function(nextValue) {
                            settingsController.setField("audio_activation_threshold", Number(nextValue.toFixed(3)))
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: "Mic sensitivity"
                            color: theme.textStrong
                            font.pixelSize: 13
                            font.weight: 500
                        }

                        Text {
                            text: Number(settingsController.settings.audio_activation_threshold || 0.02).toFixed(3)
                            color: theme.textWeak
                            font.pixelSize: 13
                            font.weight: 500
                        }

                        Item { Layout.fillWidth: true }

                        OcButton {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            variant: "secondary"
                            iconName: settingsController.audioInputTestActive ? "audio-lines" : "mic"
                            text: settingsController.audioInputTestActive ? "Stop mic test" : "Start mic test"
                            onClicked: {
                                if (settingsController.audioInputTestActive) {
                                    settingsController.stopAudioInputTest()
                                } else {
                                    settingsController.startAudioInputTest()
                                }
                            }
                        }
                    }
                }
            }

            FieldCard {
                theme: window.appTheme
                title: "Turn Timing"
                description: "Adjust how long Glance waits, listens, and keeps pre-speech context for each spoken turn."
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    LabeledTextField {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "history"
                        label: "Silence timeout"
                        helperText: "How long silence must last before Glance finishes the current spoken turn, in seconds."
                        errorText: settingsController.errors.audio_silence_seconds || ""
                        value: String(settingsController.settings.audio_silence_seconds || "")
                        suffixText: "s"
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("audio_silence_seconds", nextValue) }
                    }

                    LabeledTextField {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "clock-3"
                        label: "Wait for speech"
                        helperText: "Maximum time to wait for speech before live mode returns to listening, in seconds."
                        errorText: settingsController.errors.audio_max_wait_seconds || ""
                        value: String(settingsController.settings.audio_max_wait_seconds || "")
                        suffixText: "s"
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("audio_max_wait_seconds", nextValue) }
                    }

                    LabeledTextField {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "audio-lines"
                        label: "Max turn length"
                        helperText: "Hard limit for one captured spoken turn, in seconds."
                        errorText: settingsController.errors.audio_max_record_seconds || ""
                        value: String(settingsController.settings.audio_max_record_seconds || "")
                        suffixText: "s"
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("audio_max_record_seconds", nextValue) }
                    }

                    LabeledTextField {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        iconName: "mic"
                        label: "Pre-roll"
                        helperText: "Extra audio kept just before speech starts, in seconds."
                        errorText: settingsController.errors.audio_preroll_seconds || ""
                        value: String(settingsController.settings.audio_preroll_seconds || "")
                        suffixText: "s"
                        Layout.fillWidth: true
                        onValueEdited: function(nextValue) { settingsController.setField("audio_preroll_seconds", nextValue) }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Item { Layout.fillWidth: true }

                        OcButton {
                            theme: window.appTheme
                            iconLibrary: window.iconLibrary
                            variant: "ghost"
                            iconName: "rotate-ccw"
                            text: "Reset audio defaults"
                            onClicked: settingsController.resetAudioDefaults()
                        }
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
                description: "Manage how much session history stays on this device."
                Layout.fillWidth: true

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "history"
                    label: "History length"
                    helperText: "Maximum number of saved sessions."
                    errorText: settingsController.errors.history_length || ""
                    value: String(settingsController.settings.history_length || "")
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("history_length", nextValue) }
                }

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: "Delete saved history"
                        color: theme.textStrong
                        font.pixelSize: 13
                        font.weight: 500
                    }

                    Item { Layout.fillWidth: true }

                    OcButton {
                        theme: window.appTheme
                        iconLibrary: window.iconLibrary
                        variant: "danger"
                        iconName: "trash-2"
                        text: "Delete history"
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
                title: "General"
                description: "Appearance and prompt settings for this device."
                Layout.fillWidth: true

                LabeledComboBox {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "sun-moon"
                    label: "Theme"
                    helperText: "Choose light, dark, or system."
                    value: settingsController.settings.theme_preference || "dark"
                    options: settingsController.themeOptions
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("theme_preference", nextValue) }
                }

                LabeledTextField {
                    theme: window.appTheme
                    iconLibrary: window.iconLibrary
                    iconName: "message-square-quote"
                    label: "System prompt override"
                    helperText: "Optional custom system prompt."
                    value: settingsController.settings.system_prompt_override || ""
                    multiline: true
                    Layout.fillWidth: true
                    onValueEdited: function(nextValue) { settingsController.setField("system_prompt_override", nextValue) }
                }
            }
        }
    }

    function sectionTitle(section) {
        if (section === "api") return "API"
        if (section === "voice") return "Speech"
        if (section === "capture") return "Capture"
        if (section === "audio") return "Audio"
        if (section === "history") return "History"
        return "General"
    }

    function sectionDescription(section) {
        if (section === "api") return "Switch between compact provider panels for the response, transcription, and speech stack."
        if (section === "voice") return "Choose the speaking voice, preview it from the dropdown, and set the fallback language."
        if (section === "capture") return "Control screen sampling and response batching."
        if (section === "audio") return "Choose devices, calibrate the microphone, and tune spoken turn timing."
        if (section === "history") return "Manage locally saved sessions."
        return "Adjust the theme and optional prompt override."
    }
}
