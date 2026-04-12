import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var theme
    property var iconLibrary
    property string label: ""
    property string helperText: ""
    property string errorText: ""
    property string iconName: ""
    property string value: ""
    property bool secret: false
    property bool multiline: false

    signal valueEdited(string value)

    Layout.fillWidth: true
    implicitWidth: 620
    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        spacing: 6

        Text {
            text: root.label
            color: root.errorText.length > 0 ? theme.textOnCriticalBase : theme.textWeak
            font.pixelSize: 13
            font.weight: 500
        }

        Rectangle {
            id: wrapper
            Layout.fillWidth: true
            implicitHeight: root.multiline ? 96 : 32
            radius: 8
            color: root.errorText.length > 0 ? theme.surfaceCriticalWeak : theme.controlSurface
            border.width: 1
            border.color: root.errorText.length > 0
                ? theme.borderCriticalSelected
                : theme.controlOutline

            Behavior on color { ColorAnimation { duration: 140 } }
            Behavior on border.color { ColorAnimation { duration: 140 } }

            Rectangle {
                anchors.fill: parent
                anchors.margins: -3
                radius: 9
                color: "transparent"
                border.width: (textField.activeFocus || textArea.activeFocus) ? 1 : 0
                border.color: theme.controlOutline
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 10
                anchors.topMargin: root.multiline ? 8 : 0
                anchors.bottomMargin: root.multiline ? 8 : 0
                spacing: 10

                Image {
                    visible: root.iconName.length > 0
                    source: root.iconLibrary ? root.iconLibrary.svgData(root.iconName, theme.iconBase) : ""
                    sourceSize.width: 16
                    sourceSize.height: 16
                    fillMode: Image.PreserveAspectFit
                    Layout.preferredWidth: visible ? 16 : 0
                    Layout.preferredHeight: visible ? 16 : 0
                    Layout.alignment: root.multiline ? Qt.AlignTop : Qt.AlignVCenter
                    Layout.topMargin: root.multiline ? 4 : 0
                    Accessible.ignored: true
                }

                TextField {
                    id: textField
                    visible: !root.multiline
                    Layout.fillWidth: true
                    clip: true
                    text: root.value
                    color: theme.textStrong
                    placeholderTextColor: theme.textWeak
                    font.pixelSize: 14
                    font.weight: 400
                    selectByMouse: true
                    selectionColor: theme.surfaceBaseActive
                    selectedTextColor: theme.textStrong
                    echoMode: root.secret && !revealToggle.checked ? TextInput.Password : TextInput.Normal
                    background: null
                    Accessible.name: root.label
                    onTextEdited: root.valueEdited(text)
                }

                TextArea {
                    id: textArea
                    visible: root.multiline
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    text: root.value
                    color: theme.textStrong
                    placeholderTextColor: theme.textWeak
                    font.pixelSize: 14
                    font.weight: 400
                    wrapMode: Text.Wrap
                    selectByMouse: true
                    selectionColor: theme.surfaceBaseActive
                    selectedTextColor: theme.textStrong
                    background: null
                    Accessible.name: root.label
                    onTextChanged: root.valueEdited(text)
                }

                Button {
                    id: revealToggle
                    visible: root.secret
                    checkable: true
                    hoverEnabled: true
                    implicitWidth: 28
                    implicitHeight: 28
                    Layout.alignment: Qt.AlignVCenter
                    Accessible.name: checked ? "Hide secret" : "Show secret"
                    contentItem: Image {
                        source: root.iconLibrary ? root.iconLibrary.svgData("eye", revealToggle.hovered ? theme.iconHover : theme.iconBase) : ""
                        sourceSize.width: 16
                        sourceSize.height: 16
                        fillMode: Image.PreserveAspectFit
                        Accessible.ignored: true
                    }
                    background: Rectangle {
                        radius: 4
                        color: revealToggle.down ? theme.surfaceBaseActive : (revealToggle.hovered ? theme.surfaceBaseHover : "transparent")

                        Behavior on color { ColorAnimation { duration: 120 } }
                    }
                }
            }
        }

        Text {
            visible: root.errorText.length > 0 || root.helperText.length > 0
            text: root.errorText.length > 0 ? root.errorText : root.helperText
            color: root.errorText.length > 0 ? theme.textOnCriticalBase : theme.textWeak
            font.pixelSize: 13
            font.weight: root.errorText.length > 0 ? 500 : 400
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
