import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var theme
    property var iconLibrary
    property string label: ""
    property string helperText: ""
    property string value: ""
    property var options: []

    signal valueEdited(string value)

    Layout.fillWidth: true
    implicitWidth: 620
    implicitHeight: column.implicitHeight

    ColumnLayout {
        id: column
        anchors.fill: parent
        spacing: 6

        Text {
            text: root.label
            color: theme.textWeak
            font.pixelSize: 13
            font.weight: 500
        }

        Rectangle {
            id: trigger
            Layout.fillWidth: true
            implicitHeight: 32
            clip: true
            radius: 8
            color: theme.controlSurface
            border.width: 1
            border.color: theme.controlOutline

            Behavior on color { ColorAnimation { duration: 140 } }
            Behavior on border.color { ColorAnimation { duration: 140 } }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: root.value.length > 0
                        ? root.value
                        : (root.options.length > 0 ? root.options[0] : "Select")
                    font.pixelSize: 14
                    color: theme.textStrong
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }

                Image {
                    source: root.iconLibrary ? root.iconLibrary.svgData("chevron-down", theme.iconBase) : ""
                    sourceSize.width: 16
                    sourceSize.height: 16
                    fillMode: Image.PreserveAspectFit
                    rotation: popup.opened ? 180 : 0

                    Behavior on rotation {
                        NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
                    }
                }
            }

            TapHandler {
                onTapped: {
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
            x: trigger.x
            y: trigger.y + trigger.height + 6
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
                    height: 34
                    radius: 6
                    color: delegateArea.containsMouse || root.value === modelData
                        ? theme.surfaceBaseActive
                        : "transparent"

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.right: parent.right
                        anchors.rightMargin: 12
                        text: modelData
                        color: theme.textStrong
                        font.pixelSize: 14
                        elide: Text.ElideRight
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
