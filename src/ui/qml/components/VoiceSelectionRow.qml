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
    property string previewingVoice: ""
    readonly property real pixelRatio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1

    signal valueEdited(string value)
    signal previewClicked(string voiceName)

    function currentValue() {
        if (root.value.length > 0) {
            return root.value
        }
        return root.options.length > 0 ? root.options[0] : "Select"
    }

    function popupParent() {
        return Overlay.overlay ? Overlay.overlay : root
    }

    function popupX() {
        var target = popupParent()
        var point = trigger.mapToItem(target, 0, trigger.height + 6)
        return Math.max(12, Math.min(point.x, target.width - popup.width - 12))
    }

    function popupY() {
        var target = popupParent()
        var point = trigger.mapToItem(target, 0, trigger.height + 6)
        return Math.max(12, point.y)
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
            color: theme.textWeak
            font.pixelSize: 13
            font.weight: 500
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 0

            Button {
                id: trigger
                Layout.fillWidth: true
                implicitHeight: 32
                hoverEnabled: true
                Accessible.name: root.label

                contentItem: RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    Image {
                        visible: root.iconName.length > 0
                        source: root.iconLibrary ? root.iconLibrary.svgData(root.iconName, theme.iconBase) : ""
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
                        font.pixelSize: 14
                        color: theme.textStrong
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    Image {
                        source: root.iconLibrary ? root.iconLibrary.svgData("chevron-down", theme.iconBase) : ""
                        sourceSize.width: Math.round(16 * root.pixelRatio)
                        sourceSize.height: Math.round(16 * root.pixelRatio)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        Layout.alignment: Qt.AlignVCenter
                        rotation: popup.opened ? 180 : 0

                        Behavior on rotation {
                            NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
                        }
                    }
                }

                background: Rectangle {
                    radius: 8
                    color: trigger.down ? theme.surfaceBaseActive : (trigger.hovered ? theme.surfaceBaseHover : theme.controlSurface)
                    border.width: 1
                    border.color: theme.controlOutline

                    Behavior on color { ColorAnimation { duration: 140 } }
                    Behavior on border.color { ColorAnimation { duration: 140 } }
                }

                onClicked: {
                    if (popup.opened) {
                        popup.close()
                    } else {
                        popup.open()
                    }
                }
            }
        }

        Popup {
            id: popup
            parent: root.popupParent()
            x: root.popupX()
            y: root.popupY()
            width: trigger.width
            padding: 4
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

            background: Rectangle {
                radius: 10
                color: theme.controlSurface
                border.width: 1
                border.color: theme.controlOutline
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
                id: optionList
                implicitHeight: Math.min(contentHeight, 220)
                clip: true
                spacing: 2
                model: root.options

                delegate: Rectangle {
                    width: optionList.width
                    height: 38
                    radius: 6
                    color: delegateArea.containsMouse || selectionArea.containsMouse || root.value === modelData
                        ? theme.surfaceBaseActive
                        : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10

                        Item {
                            id: selectionArea
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            Text {
                                anchors.fill: parent
                                text: modelData
                                color: theme.textStrong
                                font.pixelSize: 14
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }

                            MouseArea {
                                id: delegateArea
                                anchors.fill: parent
                                hoverEnabled: true

                                onClicked: {
                                    root.valueEdited(modelData)
                                    popup.close()
                                }
                            }
                        }

                        OcButton {
                            id: previewButton
                            theme: root.theme
                            iconLibrary: root.iconLibrary
                            variant: root.previewingVoice === modelData ? "secondary" : "ghost"
                            iconName: root.previewingVoice === modelData ? "audio-lines" : "play"
                            text: ""
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 32
                            accessibleLabel: root.previewingVoice === modelData
                                ? "Previewing " + modelData
                                : "Preview " + modelData
                            onClicked: root.previewClicked(modelData)
                        }
                    }
                }
            }
        }

        Text {
            visible: root.helperText.length > 0
            text: root.helperText
            color: theme.textWeak
            font.pixelSize: 13
            font.weight: 400
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
