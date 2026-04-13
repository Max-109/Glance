pragma ComponentBehavior: Bound

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

Item {
    id: root

    property var theme
    property var iconLibrary
    property string label: ""
    property string helperText: ""
    property string iconName: "mic"
    property string value: ""
    property var options: []
    property var optionLabels: ({})
    property string previewingVoice: ""
    property bool previewEnabled: true
    readonly property real pixelRatio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1

    signal valueEdited(string value)
    signal previewClicked(string voiceName)

    function indexForValue() {
        var index = root.options.indexOf(root.value)
        if (index >= 0) {
            return index
        }
        return root.options.length > 0 ? 0 : -1
    }

    function currentValue() {
        if (voiceCombo.currentIndex < 0) {
            return "Select"
        }
        var currentOption = root.options[voiceCombo.currentIndex]
        if (root.optionLabels && root.optionLabels[currentOption]) {
            return root.optionLabels[currentOption]
        }
        return currentOption
    }

    Layout.fillWidth: true
    implicitWidth: 620
    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        spacing: 6

        Text {
            text: root.label
            color: root.theme.textWeak
            font.pixelSize: 13
            font.weight: 500
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            ComboBox {
                id: voiceCombo
                Layout.fillWidth: true
                implicitHeight: 32
                model: root.options
                currentIndex: root.indexForValue()
                hoverEnabled: true
                Accessible.name: root.label

                onActivated: (index) => root.valueEdited(root.options[index])

                background: Rectangle {
                    radius: 8
                    color: voiceCombo.pressed
                        ? root.theme.surfaceBaseActive
                        : (voiceCombo.hovered ? root.theme.surfaceBaseHover : root.theme.controlSurface)
                    border.width: 1
                    border.color: voiceCombo.visualFocus || voiceCombo.popup.visible
                        ? root.theme.borderSelected
                        : root.theme.controlOutline

                    Behavior on color { ColorAnimation { duration: 140 } }
                    Behavior on border.color { ColorAnimation { duration: 140 } }
                }

                indicator: Image {
                    source: root.iconLibrary ? root.iconLibrary.svgData("chevron-down", root.theme.iconBase) : ""
                    width: 16
                    height: 16
                    sourceSize.width: Math.round(16 * root.pixelRatio)
                    sourceSize.height: Math.round(16 * root.pixelRatio)
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    x: Math.round(voiceCombo.width - width - 12)
                    y: Math.round((voiceCombo.height - height) / 2)
                    rotation: voiceCombo.popup.visible ? 180 : 0
                    Accessible.ignored: true

                    Behavior on rotation {
                        NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
                    }
                }

                contentItem: Item {
                    implicitHeight: 32

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 34
                        spacing: 10

                        Image {
                            visible: root.iconName.length > 0
                            source: root.iconLibrary ? root.iconLibrary.svgData(root.iconName, root.theme.iconBase) : ""
                            sourceSize.width: Math.round(16 * root.pixelRatio)
                            sourceSize.height: Math.round(16 * root.pixelRatio)
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            Layout.preferredWidth: visible ? 16 : 0
                            Layout.preferredHeight: visible ? 16 : 0
                            Accessible.ignored: true
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.currentValue()
                            color: root.theme.textStrong
                            font.pixelSize: 14
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }

                delegate: ItemDelegate {
                    id: delegateRoot
                    required property int index
                    required property string modelData
                    width: voiceCombo.width - 8
                    implicitHeight: 38
                    highlighted: voiceCombo.highlightedIndex === index
                    hoverEnabled: true
                    padding: 0

                    background: Rectangle {
                        radius: 6
                        color: delegateRoot.highlighted || voiceCombo.currentIndex === delegateRoot.index
                            ? root.theme.surfaceBaseActive
                            : "transparent"
                    }

                    contentItem: Text {
                        text: root.optionLabels && root.optionLabels[delegateRoot.modelData]
                            ? root.optionLabels[delegateRoot.modelData]
                            : delegateRoot.modelData
                        color: root.theme.textStrong
                        font.pixelSize: 14
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 12
                        rightPadding: 12
                    }
                }

                popup: Popup {
                    y: voiceCombo.height + 6
                    width: voiceCombo.width
                    margins: 12
                    padding: 4
                    modal: true
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                    Overlay.modal: Rectangle {
                        color: root.theme.surfaceBase
                    }

                    background: Rectangle {
                        radius: 10
                        color: root.theme.controlSurface
                        border.width: 1
                        border.color: root.theme.controlOutline
                    }

                    enter: Transition {
                        ParallelAnimation {
                            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 110 }
                            NumberAnimation { property: "scale"; from: 0.98; to: 1.0; duration: 140; easing.type: Easing.OutCubic }
                        }
                    }

                    exit: Transition {
                        ParallelAnimation {
                            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 90 }
                            NumberAnimation { property: "scale"; from: 1.0; to: 0.985; duration: 90; easing.type: Easing.OutCubic }
                        }
                    }

                    contentItem: ListView {
                        clip: true
                        implicitHeight: Math.min(contentHeight, 220)
                        model: voiceCombo.popup.visible ? voiceCombo.delegateModel : null
                        currentIndex: voiceCombo.highlightedIndex
                        spacing: 2
                        ScrollIndicator.vertical: ScrollIndicator {}
                    }
                }
            }

            OcButton {
                theme: root.theme
                iconLibrary: root.iconLibrary
                variant: root.previewingVoice === root.value ? "secondary" : "ghost"
                iconName: root.previewingVoice === root.value ? "audio-lines" : "play"
                text: ""
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                enabled: root.previewEnabled && voiceCombo.currentIndex >= 0
                accessibleLabel: root.previewingVoice === root.value
                    ? "Previewing " + root.currentValue()
                    : "Preview " + root.currentValue()
                onClicked: root.previewClicked(root.options[voiceCombo.currentIndex])
            }
        }

        Text {
            visible: root.helperText.length > 0
            text: root.helperText
            color: root.theme.textWeak
            font.pixelSize: 13
            font.weight: 400
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
