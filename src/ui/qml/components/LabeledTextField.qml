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
    property string errorText: ""
    property string iconName: ""
    property string value: ""
    property string suffixText: ""
    property bool secret: false
    property bool multiline: false
    readonly property real pixelRatio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1

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
            color: root.errorText.length > 0 ? root.theme.textOnCriticalBase : root.theme.textWeak
            font.pixelSize: 13
            font.weight: 500
        }

        Rectangle {
            id: wrapper
            Layout.fillWidth: true
            implicitHeight: root.multiline ? 96 : 32
            radius: 8
            color: root.errorText.length > 0 ? root.theme.surfaceCriticalWeak : root.theme.controlSurface
            border.width: 1
            border.color: root.errorText.length > 0
                ? root.theme.borderCriticalSelected
                : ((textField.activeFocus || textArea.activeFocus) ? root.theme.borderSelected : root.theme.controlOutline)

            Behavior on color { ColorAnimation { duration: 140 } }
            Behavior on border.color { ColorAnimation { duration: 140 } }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 10
                anchors.topMargin: root.multiline ? 8 : 0
                anchors.bottomMargin: root.multiline ? 8 : 0
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
                    color: root.theme.textStrong
                    placeholderTextColor: root.theme.textWeak
                    font.pixelSize: 14
                    font.weight: 400
                    selectByMouse: true
                    selectionColor: root.theme.surfaceBaseActive
                    selectedTextColor: root.theme.textStrong
                    echoMode: root.secret && !revealToggle.checked ? TextInput.Password : TextInput.Normal
                    background: null
                    Accessible.name: root.label
                    onTextEdited: root.valueEdited(text)
                }

                Text {
                    visible: !root.multiline && root.suffixText.length > 0
                    text: root.suffixText
                    color: root.theme.textWeak
                    font.pixelSize: 13
                    font.weight: 500
                    Layout.alignment: Qt.AlignVCenter
                }

                TextArea {
                    id: textArea
                    visible: root.multiline
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    text: root.value
                    color: root.theme.textStrong
                    placeholderTextColor: root.theme.textWeak
                    font.pixelSize: 14
                    font.weight: 400
                    wrapMode: Text.Wrap
                    selectByMouse: true
                    selectionColor: root.theme.surfaceBaseActive
                    selectedTextColor: root.theme.textStrong
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
                        source: root.iconLibrary ? root.iconLibrary.svgData("eye", revealToggle.hovered ? root.theme.iconHover : root.theme.iconBase) : ""
                        sourceSize.width: Math.round(16 * root.pixelRatio)
                        sourceSize.height: Math.round(16 * root.pixelRatio)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        Accessible.ignored: true
                    }
                    background: Rectangle {
                        radius: 4
                        color: revealToggle.down ? root.theme.surfaceBaseActive : (revealToggle.hovered ? root.theme.surfaceBaseHover : "transparent")

                        Behavior on color { ColorAnimation { duration: 120 } }
                    }
                }
            }
        }

        Text {
            visible: root.errorText.length > 0 || root.helperText.length > 0
            text: root.errorText.length > 0 ? root.errorText : root.helperText
            color: root.errorText.length > 0 ? root.theme.textOnCriticalBase : root.theme.textWeak
            font.pixelSize: 13
            font.weight: root.errorText.length > 0 ? 500 : 400
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
